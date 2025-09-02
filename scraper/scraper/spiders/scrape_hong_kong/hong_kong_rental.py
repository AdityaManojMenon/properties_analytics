import json
import asyncio
import random
import scrapy
from urllib.parse import urlencode
from datetime import datetime

class HKHomesSpider(scrapy.Spider):
    name = "hong_kong_rental"
    allowed_domains = ["hongkonghomes.com"]
    

    # override via CLI: scrapy crawl HongKong_rental -a rpm=20 -a jitter=0.25
    def __init__(self, rpm: float = 20, jitter: float = 0.30, city: str = "Hong Kong",
                 start_page: int = 1, max_pages: int = 50, listing_type="for-rent", **kwargs):
        super().__init__(**kwargs)
        self.rpm = float(rpm)
        self.jitter = float(jitter)
        self.base_delay = max(0.1, 60.0 / self.rpm)
        self.current_page = int(start_page)
        self.max_pages = int(max_pages)
        self.listing_type = listing_type
        self.city = city
    
    # Add timestamp so each run has unique file
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    custom_settings = {
        "BIGQUERY_TABLE": "HK_listings_rentals",
        # BigQuery pipeline (already enabled in settings.py)
        "ITEM_PIPELINES": {
            "scraper.pipelines.BigQueryPipeline": 300,
        },
        # Local outputs
        "FEEDS": {f"outputs/hongkong/rentals_{ts}.ndjson": {"format": "jsonlines", "overwrite": True},},
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Referer": "https://hongkonghomes.com/hong-kong-property/for-rent",
            "Origin": "https://hongkonghomes.com",
            "Accept": "application/json, text/plain, */*",
        },
        # Keep concurrency at 1 so your per-page sleep governs total rate.
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "CONCURRENT_REQUESTS": 1,
        # Let our async sleep control pacing; set this to 0 (or tiny).
        "DOWNLOAD_DELAY": 0,
        "RANDOMIZE_DOWNLOAD_DELAY": False,
        "AUTOTHROTTLE_ENABLED": False,
        "COOKIES_ENABLED": False,
        # Avoid middlewares that change UA/proxy unexpectedly
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "rotating_proxies.middlewares.RotatingProxyMiddleware": None,
            "rotating_proxies.middlewares.BanDetectionMiddleware": None,
        },
    }
    CITY = "Hong Kong"

    def _url(self, page: int) -> str:
        qs = urlencode({"listing_type": self.listing_type, "currency": "hkd", "page": page})
        return f"https://hongkonghomes.com/api/en/property-search?{qs}"

    def start_requests(self):
        yield scrapy.Request(self._url(self.current_page), callback=self.parse, meta={"page": self.current_page})

    async def parse(self, response):
        data = json.loads(response.text)
        listings = data.get("data") or []

    
        for item in listings:
            yield {
                "listing_id": str(item.get("pro_id")),
                "building": item.get("build_name_eng_display"),
                "city": self.city,
                "district": item.get("pvc_name_eng") or item.get("pvc_name"),
                "size_saleable": item.get("unit_size_saleable"),
                "beds": item.get("unit_bed"),
                "baths": item.get("unit_bath"),
                "rental_ask": item.get("rental_ask"),
                "lat": (item.get("coor") or {}).get("lat"),
                "lng": (item.get("coor") or {}).get("lng"),
            }

        # stop conditions
        page = response.meta.get("page", 1)
        if not listings:
            self.logger.info("No listings on page %s — stopping.", page)
            return
        if page - (self.current_page - 1) >= self.max_pages:
            self.logger.info("Reached max_pages (%s) — stopping.", self.max_pages)
            return

        # controlled, jittered delay
        factor = 1 + random.uniform(-self.jitter, self.jitter)
        delay = max(0.1, self.base_delay * factor)
        next_page = page + 1
        self.logger.info("Waiting %.2fs before requesting page %s…", delay, next_page)
        await asyncio.sleep(delay)

        yield scrapy.Request(self._url(next_page), callback=self.parse, meta={"page": next_page})
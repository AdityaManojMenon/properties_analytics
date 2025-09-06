import json
import asyncio
import random
import scrapy
from urllib.parse import urlencode
from datetime import datetime

class HKHomesSpider(scrapy.Spider):
    name = "hong_kong_rental"
    allowed_domains = ["hongkonghomes.com"]

    def __init__(self, rpm: float = 5, jitter: float = 0.25, city: str = "Hong Kong",
                 start_page: int = 1, max_pages: int = 300, listing_type="for-rent", **kwargs):
        super().__init__(**kwargs)
        self.rpm = float(rpm)  # 5 requests/minute or 300 requests/hour
        self.jitter = float(jitter)  # +/- 25%
        self.base_delay = 60/self.rpm  # ~12s per request
        self.current_page = int(start_page)
        self.max_pages = int(max_pages)
        self.listing_type = listing_type
        self.city = city

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    custom_settings = {
        "BIGQUERY_TABLE": "HK_listings_rentals",
        # BigQuery pipeline (already enabled in settings.py)
        "ITEM_PIPELINES": {"scraper.pipelines.BigQueryPipeline": 300,},
        # Local outputs
        "FEEDS": {f"outputs/hongkong/rentals_{ts}.ndjson": {"format": "jsonlines", "overwrite": True},},
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Referer": "https://hongkonghomes.com/hong-kong-property/for-rent",
            "Origin": "https://hongkonghomes.com",
            "Accept": "application/json, text/plain, */*",
        },
        # Keep concurrency at 1 so your per-page sleep governs total rate.
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
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

    city = "Hong Kong"

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

        page = response.meta.get("page", 1)
        if not listings or (page - (self.current_page - 1) >= self.max_pages):
            return

        factor = 1 + random.uniform(-self.jitter, self.jitter)
        delay = max(10, self.base_delay * factor)  # ~12s ± 25%
        next_page = page + 1
        self.logger.info("Waiting %.2fs before requesting page %s…", delay, next_page)
        await asyncio.sleep(delay)

        yield scrapy.Request(self._url(next_page), callback=self.parse, meta={"page": next_page})

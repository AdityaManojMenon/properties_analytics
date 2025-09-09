import scrapy
import json
import random
import asyncio
from urllib.parse import urlencode
from datetime import datetime

class RedfinSFRentalSpider(scrapy.Spider):
    name = "sf_rental"
    allowed_domains = ["redfin.com"]

    def __init__(self, rpm: float = 5, jitter: float = 0.25, start_index: int = 0, max_pages: int = 300, **kwargs):
        super().__init__(**kwargs)
        self.rpm = float(rpm)
        self.jitter = float(jitter)
        self.base_delay = 60 / self.rpm
        self.start_index = int(start_index)
        self.max_pages = int(max_pages)

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    custom_settings = {
        "BIGQUERY_TABLE": "SF_listings_rentals",
        "ITEM_PIPELINES": {"scraper.pipelines.BigQueryPipeline": 300},
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 0,
        "RANDOMIZE_DOWNLOAD_DELAY": False,
        "AUTOTHROTTLE_ENABLED": False,
        "FEEDS": {
            f"outputs/sf/rentals.ndjson": {"format": "jsonlines", "overwrite": True}
        },
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.redfin.com/city/30749/CA/San-Francisco",
        },
    }

    def _url(self, start: int) -> str:
        params = {"al": 1,"market": "socal","isRentals": "true","num_homes": 20, "start": start,"region_id": 30749,"region_type": 6,}
        return f"https://www.redfin.com/stingray/api/gis?{urlencode(params)}"

    def start_requests(self):
        yield scrapy.Request(self._url(self.start_index),callback=self.parse_json,meta={"start_index": self.start_index},)

    async def parse_json(self, response):
        text = response.text
        if text.startswith("{}&&"):
            text = text[4:]

        data = json.loads(text)
        homes = data.get("payload", {}).get("homes", [])

        for home in homes:
            yield {
                "listing_id": str(home.get("listingId")),
                "address": f"{home.get('streetLine', {}).get('value', '')}, {home.get('city')}, {home.get('state')} {home.get('zip')}",
                "price": home.get("price", {}).get("value"),
                "beds": home.get("beds"),
                "baths": home.get("baths"),
                "sqft": home.get("sqFt", {}).get("value"),
                "url": f"https://www.redfin.com{home.get('url')}",
                "neighborhood": home.get("location", {}).get("value"),
                "lat": (home.get("latLong") or {}).get("value", {}).get("latitude"),
                "lng": (home.get("latLong") or {}).get("value", {}).get("longitude"),
            }

        start_index = response.meta.get("start_index", 0)
        if not homes or start_index >= self.max_pages * 20:
            return

        # Delay with jitter
        factor = 1 + random.uniform(-self.jitter, self.jitter)
        delay = max(10, self.base_delay * factor)
        next_start = start_index + 20

        self.logger.info("Waiting %.2fs before requesting start=%s…", delay, next_start)
        await asyncio.sleep(delay)

        yield scrapy.Request(self._url(next_start),callback=self.parse_json,meta={"start_index": next_start},)

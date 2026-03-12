import scrapy
import json
import asyncio
import random
from urllib.parse import urlencode
from datetime import datetime, timezone

from scraper.utils.http import build_headers
from scraper.utils.identity import make_event_id
from scraper.utils.timing import human_delay
from scraper.utils.parsing import nested_value
from scraper.settings_override import SCRAPER_DEFAULT_SETTINGS


class RedfinSpider(scrapy.Spider):

    name = "redfin"
    allowed_domains = ["redfin.com"]

    custom_settings = {
        **SCRAPER_DEFAULT_SETTINGS,
        "ITEM_PIPELINES": {"scraper.pipelines.BigQueryPipeline": 300},
    }

    SAFE_LIMIT = 20000
    STRIDE = 2000
    PAGES_PER_RUN = 100

    def __init__(
        self,
        city=None,
        region_id=None,
        market=None,
        listing_type="rental",
        run_seed=0,
        rpm=5,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if not city or not region_id or not market:
            raise ValueError("city, region_id, and market are required")

        self.city = city
        self.region_id = region_id
        self.market = market
        self.listing_type = listing_type

        self.bq_table = f"{city}_{listing_type}"

        self.run_seed = int(run_seed)
        self.rpm = float(rpm)
        self.base_delay = 60 / self.rpm

        jitter = random.randint(0, 500)

        self.start_index = ((self.run_seed * self.STRIDE) + jitter) % self.SAFE_LIMIT
        self.end_index = self.start_index + (self.PAGES_PER_RUN * 20)

        self.records_scraped = 0
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    def _url(self, start):

        params = {
            "al": 1,
            "market": self.market,
            "isRentals": "true" if self.listing_type == "rental" else "false",
            "num_homes": 20,
            "start": start,
            "region_id": self.region_id,
            "region_type": 6,
        }

        return f"https://www.redfin.com/stingray/api/gis?{urlencode(params)}"

    def start_requests(self):

        yield scrapy.Request(
            self._url(self.start_index),
            callback=self.parse_json,
            meta={"start_index": self.start_index},
            headers=build_headers(),
        )

    async def parse_json(self, response):

        text = response.text

        if text.startswith("{}&&"):
            text = text[4:]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            self.logger.warning("JSON decode error")
            return

        homes = data.get("payload", {}).get("homes", [])

        if not homes:
            return

        for home in homes:

            observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

            raw_id = home.get("listingId")
            if not raw_id:
                continue

            listing_id = str(raw_id)

            yield {
                "run_id": self.run_id,
                "event_id": make_event_id(listing_id, observed_at),
                "listing_id": listing_id,
                "price": nested_value(home, "price", "value"),
                "beds": home.get("beds"),
                "baths": home.get("baths"),
                "sqft": nested_value(home, "sqFt", "value"),
                "lat": nested_value(home, "latLong", "value", "latitude"),
                "lng": nested_value(home, "latLong", "value", "longitude"),
                "url": f"https://www.redfin.com{home.get('url')}",
                "source": "redfin",
                "listing_type": self.listing_type,
                "city": self.city,
                "country": "USA",
                "observed_at": observed_at,
                "page_block": response.meta.get("start_index", 0),
                "rpm": self.rpm,
                "block_size": self.PAGES_PER_RUN * 20,
            }

            self.records_scraped += 1

        next_start = response.meta.get("start_index", 0) + 20

        if next_start >= self.end_index:
            self.logger.info("Run complete with %s records", self.records_scraped)
            return

        await asyncio.sleep(human_delay(self.base_delay))

        yield scrapy.Request(
            self._url(next_start),
            callback=self.parse_json,
            meta={"start_index": next_start},
            headers=build_headers(),
        )
import scrapy
import json
import asyncio
from urllib.parse import urlencode
from datetime import datetime
from scraper.utils.http import build_headers
from scraper.utils.identity import make_event_id
from scraper.utils.timing import human_delay
from scraper.utils.parsing import nested_value
from scraper.settings_override import SCRAPER_DEFAULT_SETTINGS


class RedfinChicagoSalesSpider(scrapy.Spider):
    name = "chicago_sales"
    bq_table = "Chicago_listings_sales"
    allowed_domains = ["redfin.com"]

    def __init__(self, rpm: float = 5, page_block : int = 0, block_size : int = 250, **kwargs):
        super().__init__(**kwargs)
        self.rpm = float(rpm)
        self.base_delay = 60 / self.rpm  # ~12s/request
        self.records_scraped = 0 #for monitoring
        # deterministic sampling controls
        self.page_block = int(page_block)
        self.block_size = int(block_size)
        self.start_index = self.page_block * self.block_size * 20
        self.end_index = self.start_index + (self.block_size * 20)
        self.run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    custom_settings = {
        **SCRAPER_DEFAULT_SETTINGS,
        "BIGQUERY_TABLE": "Chicago_listings_sales",
        "ITEM_PIPELINES": {"scraper.pipelines.BigQueryPipeline": 300},
    }

    def _url(self, start: int) -> str:
        params = {"al": 1,"market": "chicago","isRentals": "false","num_homes": 20, 
        "start": start,"region_id": 29470,"region_type": 6,}
        return f"https://www.redfin.com/stingray/api/gis?{urlencode(params)}"

    def start_requests(self):
        yield scrapy.Request(self._url(self.start_index),callback=self.parse_json,
            meta={"start_index": self.start_index},
            headers=build_headers(),
        )

    async def parse_json(self, response):
        text = response.text
        if text.startswith("{}&&"):
            text = text[4:]
        data = json.loads(text)

        if "payload" not in data:
            self.logger.warning("Missing payload — skipping response")
            return

        homes = data.get("payload", {}).get("homes", [])

        if not homes:
            self.logger.debug("No homes returned for this page.")

        for home in homes:
            observed_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z" #UTC ISO With Z
            raw_id = home.get("listingId")

            if not raw_id:
                continue
            listing_id = str(raw_id)

            yield {
                "run_id": self.run_id, # for debugging and tracing scrapes
                "event_id": make_event_id(listing_id, observed_at),
                "listing_id": listing_id,
                "price": nested_value(home, "price", "value"),
                "beds": home.get("beds"),
                "baths": home.get("baths"),
                "sqft": nested_value(home, "sqFt", "value"),
                "lat": nested_value(home, "latLong", "value", "latitude"),
                "lng": nested_value(home, "latLong", "value", "longitude"),
                "url": f"https://www.redfin.com{home.get('url')}",
                #Some metadata added manually for each city since its important for analytics
                "source": "redfin",
                "listing_type": "sales",
                "city": "Chicago",
                "country": "USA",
                "observed_at": observed_at, # temporal column needed for metric analysis like Absorption and DOM
                "page_block": self.page_block,
                "slice_start": self.start_index,
                "block_size": self.block_size,
            }

            self.records_scraped += 1


        #Pagation Section
        start_index = response.meta["start_index"]
        next_start = start_index + 20

        if not homes or next_start >= self.end_index:
            self.logger.info("Run %s finished with %s records",
                     self.run_id, self.records_scraped)
            return

        await asyncio.sleep(human_delay(self.base_delay))
        
        yield scrapy.Request(self._url(next_start), callback = self.parse_json,
                             meta = {"start_index": next_start},
                             headers = build_headers(),
        )

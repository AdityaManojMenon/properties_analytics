import scrapy
import json
import random
import asyncio
import hashlib
from urllib.parse import urlencode
from datetime import datetime

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
]

class RedfinChicagoRentalSpider(scrapy.Spider):
    name = "chicago_rental"
    allowed_domains = ["redfin.com"]

    def __init__(self, rpm: float = 5, jitter: float = 0.25, page_block : int = 0, 
                 block_size : int = 50, max_pages: int = 300, **kwargs):
        super().__init__(**kwargs)
        self.rpm = float(rpm)
        self.jitter = float(jitter)
        self.base_delay = 60 / self.rpm  # ~12s/request
        self.records_scraped = 0 #for monitoring
        # deterministic sampling controls
        self.page_block = int(page_block)
        self.block_size = int(block_size)
        self.max_pages = int(max_pages)
        self.start_index = self.page_block * self.block_size * 20
        self.end_index = self.start_index + (self.block_size * 20)
        self.run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    custom_settings = {
        "BIGQUERY_TABLE": "Chicago_listings_rentals",
        "ITEM_PIPELINES": {"scraper.pipelines.BigQueryPipeline": 300},
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 0,
        "RANDOMIZE_DOWNLOAD_DELAY": False,
        "AUTOTHROTTLE_ENABLED": True, #Just a safety net for edge cases the human_delay function control pace
        "AUTOTHROTTLE_START_DELAY": 5,
        "AUTOTHROTTLE_MAX_DELAY": 60,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [429, 500, 502, 503, 504],
        "DOWNLOAD_TIMEOUT": 30,
    }

    def _url(self, start: int) -> str:
        params = {"al": 1,"market": "chicago","isRentals": "true","num_homes": 20, 
                  "start": start,"region_id": 29470,"region_type": 6,}
        return f"https://www.redfin.com/stingray/api/gis?{urlencode(params)}"

    def start_requests(self):
        yield scrapy.Request(self._url(self.start_index),callback=self.parse_json,
                             meta={"start_index": self.start_index},
                             headers={"User-Agent": random.choice(USER_AGENTS),
                                      "Accept-Language": "en-US,en;q=0.9"})
    
    #Maintain Idempotency
    def make_event_id(self,listing_id, scraped_at):
        return hashlib.md5(f"{listing_id}-{scraped_at}".encode()).hexdigest()
    
    #Creating a more human like delay since not using rotating proxies 
    def human_delay(self):
        factor = random.uniform(0.7, 1.6)
        delay = max(8, self.base_delay * factor)

        # occasional longer pause (simulate browsing)
        if random.random() < 0.07:
            delay += random.uniform(20, 60)

        return delay

    async def parse_json(self, response):
        text = response.text
        if text.startswith("{}&&"):
            text = text[4:]
        data = json.loads(text)

        if "payload" not in data:
            self.logger.warning("Missing payload therefore skipping response")
            return
        
        homes = data.get("payload", {}).get("homes", [])

        #Yield specific columns from scrape for bronze layer
        for home in homes:
            scraped_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z" #UTC ISO With Z
            listing_id = str(home.get("listingId"))
            yield {
                "run_id": self.run_id, # for debugging and tracing scrapes
                "event_id": self.make_event_id(listing_id, scraped_at),
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
                #Some metadata added manually for each city since its important for analytics
                "source": "redfin",
                "listing_type": "rental",
                "city": "Chicago",
                "country": "USA",
                "scraped_at": scraped_at # temporal column needed for metric analysis like Absorption and DOM
            }
            self.records_scraped += 1 
        
        #Useful when prefect monitors runs
        self.logger.info("Run %s scraped %s records", self.run_id, self.records_scraped)

        #Pagation Section
        start_index = response.meta.get("start_index", 0)
        next_start = start_index + 20

        if not homes or next_start >= self.end_index:
            self.logger.info("Finished assigned block.")
            return

        delay = self.human_delay()
        self.logger.info("Sleeping %.2fs before next request...", delay)
        await asyncio.sleep(delay)
        
        yield scrapy.Request(self._url(next_start),callback=self.parse_json,
                             meta={"start_index": next_start},
                             headers={"User-Agent": random.choice(USER_AGENTS),
                                      "Accept-Language": "en-US,en;q=0.9"}
        )
        

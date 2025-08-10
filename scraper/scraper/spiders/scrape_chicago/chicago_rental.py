import scrapy
import json
import time


class RedfinChicagoRentalSpider(scrapy.Spider):
    name = "chicago_rental"
    allowed_domains = ["redfin.com"]

    #got this from inspecting the network tab in the browser
    api_url = "https://www.redfin.com/stingray/api/gis?al=1&clustering_threshold=350&country_code=US&ep=true&isRentals=true&lpp=20&market=chicago&mpt=99&num_homes=350&ord=redfin-recommended-asc&page_number=1&poly=-87.66189%2041.84023%2C-87.60833%2041.84023%2C-87.60833%2041.95383%2C-87.66189%2041.95383%2C-87.66189%2041.84023&region_id=29470&region_type=6&sf=1,2,3,5,6,7&start=0&status=9&uipt=1,2,3,4&v=8&zoomLevel=13"

    custom_settings = {
        "FEEDS": {"chicago_sales.json": {"format": "json", "overwrite": True}},
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.redfin.com/city/29470/IL/Chicago",
        },
    }

    def start_requests(self):
        yield scrapy.Request(url=self.api_url, callback=self.parse_json)

    def parse_json(self, response):
        text = response.text
        if text.startswith("{}&&"):
            text = text[4:]  # Remove "{}&&" prefix

        data = json.loads(text)
        homes = data.get("payload", {}).get("homes", [])

        for home in homes:
            yield {
                "address": f"{home.get('streetLine', {}).get('value', '')}, {home.get('city')}, {home.get('state')} {home.get('zip')}",
                "price": home.get("price", {}).get("value"),
                "beds": home.get("beds"),
                "baths": home.get("baths"),
                "sqft": home.get("sqFt", {}).get("value"),
                "url": f"https://www.redfin.com{home.get('url')}",
                "neighborhood": home.get("location", {}).get("value"),
                "lat": home.get("latLong", {}).get("value", {}).get("latitude"),
                "lng": home.get("latLong", {}).get("value", {}).get("longitude"),
            }

            # Add 4-second delay per listing
            self.logger.info("Sleeping for 4 seconds between listings...")
            time.sleep(4)
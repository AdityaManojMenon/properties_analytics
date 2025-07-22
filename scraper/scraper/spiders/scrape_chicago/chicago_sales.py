import scrapy
import json
import time 

class RedfinChicagoSpider(scrapy.Spider):
    name = "redfin_chicago"
    allowed_domains = ["redfin.com"]

    # Replace with a real URL from DevTools → Network tab
    api_url = "https://www.redfin.com/stingray/api/gis?al=1&market=chicago&num_homes=100&...&region_id=29470&region_type=6"

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

            # ⏱️ Add 3-second delay per listing
            self.logger.info("Sleeping for 4 seconds between listings...")
            time.sleep(4)

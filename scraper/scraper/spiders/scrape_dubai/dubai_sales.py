import scrapy
import json
import time

class PropertyfinderSalesSpider(scrapy.Spider):
    name = "dubai_sales"
    allowed_domains = ["propertyfinder.ae"]
    start_urls = ["https://www.propertyfinder.ae/en/buy/dubai/properties-for-sale.html"]

    def parse(self, response):
        current_page = response.meta.get("page", 1)
        self.logger.info(f"Scraping sales page {current_page}: {response.url}")

        if response.status != 200:
            self.logger.warning(f"Failed to load page {current_page} with status {response.status}")
            return

        data = response.css('script#__NEXT_DATA__::text').get()
        if not data:
            self.logger.warning("No JSON data found")
            return

        try:
            json_data = json.loads(data)
            listings = json_data["props"]["pageProps"]["searchResult"]["listings"]
        except (KeyError, json.JSONDecodeError):
            self.logger.warning("Could not find listings key or parse JSON.")
            return

        for listing in listings:
            prop = listing.get("property")
            if not prop:
                self.logger.warning("Skipping listing with null 'property'")
                continue

            yield {
                "id": prop.get("id"),
                "title": prop.get("title"),
                "price": prop.get("price", {}).get("value"),
                "currency": prop.get("price", {}).get("currency"),
                "bedrooms": prop.get("bedrooms"),
                "bathrooms": prop.get("bathrooms"),
                "size_sqft": prop.get("size", {}).get("value"),
                "location": prop.get("location", {}).get("full_name"),
                "agent": prop.get("agent", {}).get("name"),
                "agency": prop.get("broker", {}).get("name"),
                "is_verified": prop.get("is_verified"),
                "url": response.urljoin(prop.get("share_url")),
                "listed_date": prop.get("listed_date"),
            }

            # 👇 Add delay between each listing
            self.logger.info("Sleeping for 4 seconds before next listing...")
            time.sleep(4)

        # Temporary page limit (set for testing, remove or increase later)
        max_num_pages = 5
        next_page = current_page + 1
        if current_page < max_num_pages:
            next_url = f"https://www.propertyfinder.ae/en/buy/dubai/properties-for-sale.html?page={next_page}"
            self.logger.info(f"Requesting next page: {next_url}")
            yield scrapy.Request(next_url, callback=self.parse, meta={"page": next_page})

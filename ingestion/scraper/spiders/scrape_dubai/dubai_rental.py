import scrapy
import json
import time

class PropertyfinderRentalSpider(scrapy.Spider):
    name = "dubai_rental"
    allowed_domains = ["propertyfinder.ae"]
    start_urls = [
        "https://www.propertyfinder.ae/en/rent/dubai/properties-for-rent.html"
    ]

    def parse(self, response):
        current_page = response.meta.get("page", 1)
        self.logger.info(f"Scraping rentals page {current_page}: {response.url}")

        data = response.css("script#__NEXT_DATA__::text").get()
        if not data:
            self.logger.warning("No embedded JSON found in script tag")
            return

        try:
            json_data = json.loads(data)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON")
            return

        listings = json_data.get("props", {}) \
                            .get("pageProps", {}) \
                            .get("searchResult", {}) \
                            .get("listings", [])

        if not listings:
            self.logger.info("No more listings found. Ending crawl.")
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

            # 👇 3-second delay between listings
            self.logger.info("Sleeping for 3 seconds before next listing...")
            time.sleep(3)

        # Automatically move to the next page
        next_page = current_page + 1
        next_url = f"https://www.propertyfinder.ae/en/rent/dubai/properties-for-rent.html?page={next_page}"
        self.logger.info(f"Requesting next page: {next_url}")
        yield scrapy.Request(
            url=next_url,
            callback=self.parse,
            meta={"page": next_page}
        )

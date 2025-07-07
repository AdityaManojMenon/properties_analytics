import scrapy
import json

class PropertyfinderSalesSpider(scrapy.Spider):
    name = "propertyfinder_sales"
    allowed_domains = ["propertyfinder.ae"]
    start_urls = ["https://www.propertyfinder.ae/en/buy/dubai/properties-for-sale.html"]

    def parse(self, response):

        #checking to see if failing to load page
        current_page = response.meta.get("page",1)
        self.logger.info(f"Scraping Page {current_page}: {response.url}")
        if response.status != 200:
            self.logger.warning(f"Failed to load page {current_page} with status {response.status}")
            return
        
        #Extract embedded JSON data
        data = response.css('script#__NEXT_DATA__::text').get()
        if not data:
            self.logger.warning("No JSON data found")
            return
        
        json_data = json.loads(data) 

        try:
            listings = json_data["props"]["pageProps"]["searchResult"]["listings"]
        except KeyError:
            self.logger.warning("Could not find listings key.")
            return

        for listing in listings:
            prop = listing.get("property")
            #if the key property exists but contains value None want to loop back if None to avoid Attribute Error
            if not prop:
                self.logger.warning("Skipping a listing because property is None.")
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
        
        #hading pagation for testing want to only scrape a little since no proxy rotation implemented yet
        max_num_pages = 5
        next_page = current_page + 1
        if current_page <= max_num_pages:
            next_url = f"https://www.propertyfinder.ae/en/buy/dubai/properties-for-sale.html?page={next_page}"
            yield scrapy.Request(next_url, callback=self.parse, meta={"page": next_page})
        
        

        

import scrapy


class PropertyfinderRentalSpider(scrapy.Spider):
    name = "propertyfinder_rental"
    allowed_domains = ["propertyfinder.ae"]
    start_urls = ["https://propertyfinder.ae"]

    def parse(self, response):
        pass

import scrapy


class PropertyfinderSalesSpider(scrapy.Spider):
    name = "propertyfinder_sales"
    allowed_domains = ["propertyfinder.ae"]
    start_urls = ["https://propertyfinder.ae"]

    def parse(self, response):
        pass

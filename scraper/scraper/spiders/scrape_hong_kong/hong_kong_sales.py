import scrapy


class HongKongSalesSpider(scrapy.Spider):
    name = "hong_kong_sales"
    allowed_domains = ["hongkonghomes.com"]
    start_urls = ["https://hongkonghomes.com"]

    def parse(self, response):
        pass

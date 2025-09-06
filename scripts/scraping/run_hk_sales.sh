#!/bin/bash
source ~/Desktop/properties_analytics/.venv/bin/activate

export GOOGLE_CLOUD_PROJECT=property-investment-468818
export BIGQUERY_DATASET=scrapy_data
export BIGQUERY_TABLE=HK_listings_sales
export GOOGLE_APPLICATION_CREDENTIALS="/Users/am/Desktop/gcp/property-investment-468818-74ea0ce1c5ab.json"

cd ~/Desktop/properties_analytics/scraper

scrapy crawl hong_kong_sales -s JOBDIR=crawls/hk_sales -s DELTAFETCH_ENABLED=True

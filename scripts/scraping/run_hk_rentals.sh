#!/bin/bash
source .venv/bin/activate

export GOOGLE_CLOUD_PROJECT=property-investment-468818
export BIGQUERY_DATASET=scrapy_data
export BIGQUERY_TABLE=HK_listings_rentals
export GOOGLE_APPLICATION_CREDENTIALS="/Users/am/Desktop/gcp/property-investment-468818-74ea0ce1c5ab.json"

cd scraper
# Run with persistence & dedup
scrapy crawl hong_kong_rental -s JOBDIR=crawls/hk_rentals -s DELTAFETCH_ENABLED=True

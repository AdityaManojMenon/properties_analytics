#!/bin/bash
source ~/Desktop/properties_analytics/.venv/bin/activate

# Export env vars
export GOOGLE_CLOUD_PROJECT=property-investment-468818
export BIGQUERY_DATASET=scrapy_data
export BIGQUERY_TABLE=LA_listings_rentals   
export GOOGLE_APPLICATION_CREDENTIALS="/Users/am/Desktop/gcp/property-investment-468818-74ea0ce1c5ab.json"

# Move into Scrapy project root
cd ~/Desktop/properties_analytics/scraper

# Run spider with persistence
scrapy crawl la_rental -s JOBDIR=crawls/la_rentals -s DELTAFETCH_ENABLED=True
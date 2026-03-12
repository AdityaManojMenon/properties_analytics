from prefect import flow, task
import subprocess
import os

# BigQuery environment
ENV = {
    "GOOGLE_CLOUD_PROJECT": "property-investment-468818",
    "BIGQUERY_DATASET": "scrapy_data",
    "GOOGLE_APPLICATION_CREDENTIALS": "/Users/am/Desktop/gcp/property-investment-468818-74ea0ce1c5ab.json"
}

# Cities supported by Redfin
CITIES = [
    {"city": "Chicago", "region_id": 29470, "market": "chicago"},
    {"city": "NYC", "region_id": 30749, "market": "newyork"},
    {"city": "LA", "region_id": 11203, "market": "socal"},
    {"city": "Miami", "region_id": 11458, "market": "florida"},
    {"city": "Dallas", "region_id": 30818, "market": "dallas"},
    {"city": "Austin", "region_id": 30894, "market": "austin"},
    {"city": "Toronto", "region_id": 14328, "market": "toronto"}
]

@task
def run_spider(city, region_id, market, listing_type):
    cmd = [
        "scrapy",
        "crawl",
        "redfin",
        "-a", f"city={city}",
        "-a", f"region_id={region_id}",
        "-a", f"market={market}",
        "-a", f"listing_type={listing_type}"
    ]

    env = os.environ.copy()
    env.update(ENV)

    subprocess.run(cmd, env=env, check=True)


@flow(name="redfin-real-estate-ingestion")
def redfin_pipeline():

    for city in CITIES:
        run_spider(city["city"], city["region_id"], city["market"], "rental")
        run_spider(city["city"], city["region_id"], city["market"], "sales")


if __name__ == "__main__":
    redfin_pipeline()
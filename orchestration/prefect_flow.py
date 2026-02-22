from prefect import flow, task, get_run_logger
import subprocess
import random
import time
import os
from datetime import datetime
from pathlib import Path


SCRAPY_DIR = Path(__file__).resolve().parents[1] / "ingestion"

SPIDERS= [
    "chicago_rental",
    "chicago_sales",
]

# Define task for prefect for monitoring and logging
@task
def run_spider(spider: str, block: int):
    logger = get_run_logger()

    sleep = random.randint(60, 120)
    logger.info(f"Sleeping {sleep}s before starting {spider}")
    time.sleep(sleep)

    # Map spider to table
    table_map = {
        "chicago_rental": "Chicago_listings_rentals",
        "chicago_sales": "Chicago_listings_sales",
    }

    table = table_map[spider]

    env = os.environ.copy()

    env.update({
        "GOOGLE_CLOUD_PROJECT": "property-investment-468818",
        "BIGQUERY_DATASET": "scrapy_data",
        "BIGQUERY_TABLE": table,   
        "GOOGLE_APPLICATION_CREDENTIALS":
            "/Users/am/Desktop/gcp/property-investment-468818-74ea0ce1c5ab.json",
    })

    logger.info(f"Writing {spider} → {table}")

    process = subprocess.Popen(
        ["scrapy", "crawl", spider, "-a", f"page_block={block}","-a", "block_size=250"],
        cwd=SCRAPY_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"{spider} failed")

    logger.info(f"{spider} completed")

# Orchestrate task
@flow(name="prop-biweekly-scrape")
def biweekly_scrape():
    # This rotates which listings is observed every week. Over time covers whole market not all at once
    logger = get_run_logger()
    logger.info("Env GOOGLE_CLOUD_PROJECT = %s", os.getenv("GOOGLE_CLOUD_PROJECT"))
    block = datetime.utcnow().isocalendar().week % 3
    logger.info(f"Using sampling block {block}")
    spiders = SPIDERS[:]
    random.shuffle(spiders)
    for spider in spiders:
        run_spider(spider, block)


if __name__ == "__main__":
    biweekly_scrape()
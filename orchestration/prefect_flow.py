from prefect import flow, task, get_run_logger
import subprocess
import random
import time
import os
from datetime import datetime
from pathlib import Path

SCRAPY_DIR = Path(__file__).resolve().parents[1] / "ingestion"

SPIDERS = [
    "la_rental",
    "la_sales",
]

@task
def run_spider(spider: str, seed: int):
    logger = get_run_logger()

    stagger = random.randint(60, 180)
    logger.info(f"Pre-run stagger {stagger}s before {spider}")
    time.sleep(stagger)

    env = os.environ.copy()
    env.update({
        "GOOGLE_CLOUD_PROJECT": "property-investment-468818",
        "BIGQUERY_DATASET": "scrapy_data",
        "BIGQUERY_TABLE": table_map[spider],
        "GOOGLE_APPLICATION_CREDENTIALS":
            "/Users/am/Desktop/gcp/property-investment-468818-74ea0ce1c5ab.json",
    })

    process = subprocess.Popen(
        ["scrapy", "crawl", spider, "-a", f"run_seed={seed}"],
        cwd=SCRAPY_DIR,
        env=env,
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"{spider} failed")

    logger.info(f"{spider} completed")


@flow(name="prop-biweekly-scrape")
def biweekly_scrape():
    logger = get_run_logger()

    # changing seed daily rotates sampling window
    seed = int(datetime.utcnow().timestamp() // 86400)

    spiders = SPIDERS[:]
    random.shuffle(spiders)

    for spider in spiders:
        run_spider(spider, seed)

        cooldown = random.randint(300, 900)  # 5–15 min
        logger.info(f"Cooling down {cooldown}s")
        time.sleep(cooldown)


if __name__ == "__main__":
    biweekly_scrape()
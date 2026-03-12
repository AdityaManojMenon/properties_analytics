#pipelines.py
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import json
import datetime
from google.cloud import bigquery

class BigQueryPipeline:

    def __init__(self, project_id, dataset_id):
        if not project_id or not dataset_id:
            raise RuntimeError(
                "Missing BIGQUERY configuration. "
                "Check GOOGLE_CLOUD_PROJECT and BIGQUERY_DATASET."
            )

        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=self.project_id)

    @classmethod
    def from_crawler(cls, crawler):
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "property-investment-468818")
        dataset = os.getenv("BIGQUERY_DATASET", "scrapy_data")

        return cls(project, dataset)

    def process_item(self, item, spider):

        table_name = getattr(spider, "bq_table", None)

        if not table_name:
            raise RuntimeError(f"Spider {spider.name} missing 'bq_table' attribute.")

        row = dict(item)

        now = datetime.datetime.utcnow()

        row["source"] = spider.name

        # BigQuery streaming expects RFC3339 string, NOT datetime object
        row["scraped_at"] = now.isoformat() + "Z"

        # Ensure observed_at is string (some spiders may send datetime later)
        if isinstance(row.get("observed_at"), datetime.datetime):
            row["observed_at"] = row["observed_at"].isoformat() + "Z"

        # Raw payload must not contain datetime either
        row["raw_json"] = json.dumps(row, default=str)


        table_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"

        errors = self.client.insert_rows_json(table_ref, [row])

        if errors:
            spider.logger.error(f"BigQuery insert errors: {errors}")

        return item
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
    def __init__(self):
        # Pick up values from environment variables
        self.project_id = os.environ["GOOGLE_CLOUD_PROJECT"]      
        self.dataset_id = os.environ["BIGQUERY_DATASET"]          
        self.table_id = os.environ["BIGQUERY_TABLE"]              
        self.client = bigquery.Client(project=self.project_id)

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        row = dict(item)
        row["source"] = spider.name

        row["scraped_at"] = datetime.datetime.utcnow().isoformat()

        # Keep raw copy for debugging
        row["raw"] = json.dumps(item)

        table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        errors = self.client.insert_rows_json(table_ref, [row])
        if errors:
            spider.logger.error(f"BigQuery insert errors: {errors}")
        return item

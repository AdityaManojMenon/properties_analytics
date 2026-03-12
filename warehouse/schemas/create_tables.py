from google.cloud import bigquery
from google.api_core.exceptions import Conflict

PROJECT_ID = "property-investment-468818"
DATASET_ID = "scrapy_data"

client = bigquery.Client(project="property-investment-468818")
print("Connected to:", client.project)


cities = [
    "NYC","LA","Miami","Austin","Dallas",
    "Chicago","Toronto","Sydney","Singapore",
    "Tokyo","Madrid","Dubai","Sao_Paulo","Lisbon",
    "London"
]

listing_types = ["sales","rental"]

schema = [
    bigquery.SchemaField("run_id","STRING"),
    bigquery.SchemaField("event_id","STRING"),
    bigquery.SchemaField("listing_id","STRING",mode="REQUIRED"),
    bigquery.SchemaField("city","STRING"),
    bigquery.SchemaField("country","STRING"),
    bigquery.SchemaField("source","STRING"),
    bigquery.SchemaField("listing_type","STRING"),
    bigquery.SchemaField("price","INT64"),
    bigquery.SchemaField("beds","INT64"),
    bigquery.SchemaField("baths","FLOAT64"),
    bigquery.SchemaField("sqft","INT64"),
    bigquery.SchemaField("lat","FLOAT64"),
    bigquery.SchemaField("lng","FLOAT64"),
    bigquery.SchemaField("url","STRING"),
    bigquery.SchemaField("observed_at","TIMESTAMP",mode="REQUIRED"),
    bigquery.SchemaField("page_block","INT64"),
    bigquery.SchemaField("rpm","FLOAT64"),
    bigquery.SchemaField("block_size","INT64"),
    bigquery.SchemaField("raw_json","STRING"),
    bigquery.SchemaField("scraped_at","TIMESTAMP"),
]

client = bigquery.Client(project=PROJECT_ID)

dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"

for city in cities:
    for listing_type in listing_types:

        table_name = f"{city}_{listing_type}"
        table_id = f"{dataset_ref}.{table_name}"

        table = bigquery.Table(table_id, schema=schema)

        try:
            client.create_table(table)
            print(f"Created table {table_id}")

        except Conflict:
            print(f"Table already exists: {table_id}")

        except Exception as e:
            print(f"ERROR creating {table_id}: {e}")
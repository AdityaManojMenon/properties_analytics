from google.cloud import bigquery

# CHANGE THESE
PROJECT_ID = "property-investment-468818"
DATASET_ID = "scrapy_data"

client = bigquery.Client(project="property-investment-468818")
print("Connected to:", client.project)


dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"

tables = client.list_tables(dataset_ref)

for table in tables:
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table.table_id}"

    print(f"Dropping table: {table_id}")

    client.delete_table(table_id, not_found_ok=True)

print("All tables dropped successfully.")
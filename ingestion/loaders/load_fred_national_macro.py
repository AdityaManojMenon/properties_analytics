import pandas as pd
import time
from fredapi import Fred
from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
DATASET = os.getenv("HOUSING_RAW_DATASET")
FRED_API_KEY = os.getenv("FRED_API_KEY")


client = bigquery.Client(project=PROJECT_ID)
fred = Fred(api_key=FRED_API_KEY)

print("SUCCESS — Connected to:", client.project)

SERIES = {
    "mortgage_rate": "MORTGAGE30US",
    "inflation": "CPIAUCSL"
}

def fetch_series(code):
    data = fred.get_series(code)

    df = pd.DataFrame({
        "date": data.index,
        "value": data.values
    })

    df["series_id"] = code
    df["source"] = "fred"

    return df

def upload_table(df, table_name):

    table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"

    job = client.load_table_from_dataframe(
        df,
        table_id,
        job_config=bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            autodetect=True
        )
    )

    job.result()

    print(f"Loaded {len(df)} rows into {table_name}")

def main():
    frames = []

    for name,code in SERIES.items():
        print(f"Fetching {name} data")
        df = fetch_series(code)
        frames.append(df)
        #Avoid API throttling
        time.sleep(1)
    
    final_df = pd.concat(frames)

    upload_table(final_df, "fred_national_macro")

    print("Loaded FRED macro data")

if __name__ == "__main__":
    main()
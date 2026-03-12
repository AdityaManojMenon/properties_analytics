# ingestion/loaders/load_census.py

import requests
import pandas as pd
from google.cloud import bigquery
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
DATASET = os.getenv("HOUSING_RAW_DATASET")


CENSUS_API = "https://api.census.gov/data/2022/acs/acs5"

client = bigquery.Client(project=PROJECT_ID)


def fetch_population():
    
    params = {
        "get": "NAME,B01003_001E,B19013_001E",
        "for": "metropolitan statistical area/micropolitan statistical area:*"
    }
    

    r = requests.get(CENSUS_API, params=params)
    data = r.json()

    #df = pd.DataFrame(data[1:], columns=data[0])
    df = pd.DataFrame(data[1:], columns = data[0])
    
    df.rename(
        columns={
            "NAME": "metro",
            "B01003_001E": "population",
            "B19013_001E": "median_income",
            "metropolitan statistical area/micropolitan statistical area": "msa_id"
        },
        inplace=True
    )

    df["population"] = pd.to_numeric(df["population"])
    df["median_income"] = pd.to_numeric(df["median_income"])

    df["source"] = "census"
    
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

    census_df = fetch_population()

    print(census_df)

    upload_table(census_df, "census_population")

    print("Loaded census population data")
if __name__ == "__main__":
    main()
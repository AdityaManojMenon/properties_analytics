import pandas as pd
import requests
from io import BytesIO
from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
DATASET = os.getenv("HOUSING_RAW_DATASET")

ZILLOW_HOME_URL = "https://files.zillowstatic.com/research/public_csvs/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
ZILLOW_RENT_URL = "https://files.zillowstatic.com/research/public_csvs/zori/Metro_zori_uc_sfrcondomfr_sm_sa_month.csv"

client = bigquery.Client(project=PROJECT_ID)

print("SUCCESS — Connected to:", client.project)


def download_csv(url):
    r = requests.get(url)
    r.raise_for_status()
    return pd.read_csv(BytesIO(r.content))


def reshape_zillow(df, value_name):

    meta_cols = ["RegionID", "SizeRank", "RegionName", "RegionType", "StateName"]

    date_cols = [c for c in df.columns if c not in meta_cols]

    df_long = df.melt(
        id_vars = meta_cols,
        value_vars = date_cols,
        var_name = "date",
        value_name = value_name
    )

    df_long.rename(
        columns ={
            "RegionName": "metro",
            "StateName": "state"
        },
        inplace=True
    )

    df_long["date"] = pd.to_datetime(df_long["date"])
    df_long["source"] = "zillow"

    return df_long


def upload_table(df, table_name):
    table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True,
    )

    job = client.load_table_from_dataframe(
        df,
        table_id,
        job_config=job_config
    )

    job.result()

    print(f"Loaded {len(df)} rows into {table_name}")


def main():

    print("Downloading Zillow Home Value Index...")
    zhvi = download_csv(ZILLOW_HOME_URL)
    print(zhvi)
    zhvi = reshape_zillow(zhvi, "home_value_index")
    upload_table(zhvi, "zillow_home_values")

    print("Downloading Zillow Rent Index...")
    zori = download_csv(ZILLOW_RENT_URL)
    print(zori)
    zori = reshape_zillow(zori, "rent_index")
    upload_table(zori, "zillow_rent_index")


if __name__ == "__main__":
    main()
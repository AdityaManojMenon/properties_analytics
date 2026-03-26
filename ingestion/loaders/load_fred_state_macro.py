import pandas as pd
import time
from fredapi import Fred
from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ID  = os.getenv("GOOGLE_CLOUD_PROJECT")
DATASET     = os.getenv("HOUSING_RAW_DATASET")
FRED_API_KEY = os.getenv("FRED_API_KEY")

client = bigquery.Client(project=PROJECT_ID)
fred   = Fred(api_key=FRED_API_KEY)

print("SUCCESS — Connected to:", client.project)

# ---------------------------------------------------------------------------
# State FRED series
# Each metric maps to a FRED series ID per state.
# Columns stored: date, state, metric, value, series_id, source,
#                 frequency, seasonally_adjusted
#
# Series reference:
#   {STATE}UR      Unemployment rate          — monthly, SA
#   {STATE}BPPRIV  Private building permits   — monthly, NSA
#   {STATE}NA      Nonfarm payrolls            — monthly, SA
#   SMS{STATE}     State avg hourly earnings  — monthly, SA (SMU series)
# ---------------------------------------------------------------------------

STATE_FRED_CODES = {
    "TX": {
        "unemployment":  ("TXUR",      "monthly", True),
        "permits":       ("TXBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("TXNA",      "monthly", True),
        "hourly_wages":  ("SMU48000000500000003", "monthly", True),
    },
    "CA": {
        "unemployment":  ("CAUR",      "monthly", True),
        "permits":       ("CABPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("CANA",      "monthly", True),
        "hourly_wages":  ("SMU06000000500000003", "monthly", True),
    },
    "NY": {
        "unemployment":  ("NYUR",      "monthly", True),
        "permits":       ("NYBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("NYNA",      "monthly", True),
        "hourly_wages":  ("SMU36000000500000003", "monthly", True),
    },
    "FL": {
        "unemployment":  ("FLUR",      "monthly", True),
        "permits":       ("FLBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("FLNA",      "monthly", True),
        "hourly_wages":  ("SMU12000000500000003", "monthly", True),
    },
    "IL": {
        "unemployment":  ("ILUR",      "monthly", True),
        "permits":       ("ILBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("ILNA",      "monthly", True),
        "hourly_wages":  ("SMU17000000500000003", "monthly", True),
    },
    "MA": {
        "unemployment":  ("MAUR",      "monthly", True),
        "permits":       ("MABPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("MANA",      "monthly", True),
        "hourly_wages":  ("SMU25000000500000003", "monthly", True),
    },
    "WA": {
        "unemployment":  ("WAUR",      "monthly", True),
        "permits":       ("WABPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("WANA",      "monthly", True),
        "hourly_wages":  ("SMU53000000500000003", "monthly", True),
    },
    "VA": {
        "unemployment":  ("VAUR",      "monthly", True),
        "permits":       ("VABPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("VANA",      "monthly", True),
        "hourly_wages":  ("SMU51000000500000003", "monthly", True),
    },
    "MD": {
        "unemployment":  ("MDUR",      "monthly", True),
        "permits":       ("MDBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("MDNA",      "monthly", True),
        "hourly_wages":  ("SMU24000000500000003", "monthly", True),
    },
    "NJ": {
        "unemployment":  ("NJUR",      "monthly", True),
        "permits":       ("NJBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("NJNA",      "monthly", True),
        "hourly_wages":  ("SMU34000000500000003", "monthly", True),
    },
    "AZ": {
        "unemployment":  ("AZUR",      "monthly", True),
        "permits":       ("AZBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("AZNA",      "monthly", True),
        "hourly_wages":  ("SMU04000000500000003", "monthly", True),
    },
    "GA": {
        "unemployment":  ("GAUR",      "monthly", True),
        "permits":       ("GABPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("GANA",      "monthly", True),
        "hourly_wages":  ("SMU13000000500000003", "monthly", True),
    },
    "TN": {
        "unemployment":  ("TNUR",      "monthly", True),
        "permits":       ("TNBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("TNNA",      "monthly", True),
        "hourly_wages":  ("SMU47000000500000003", "monthly", True),
    },
    "NC": {
        "unemployment":  ("NCUR",      "monthly", True),
        "permits":       ("NCBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("NCNA",      "monthly", True),
        "hourly_wages":  ("SMU37000000500000003", "monthly", True),
    },
    "CO": {
        "unemployment":  ("COUR",      "monthly", True),
        "permits":       ("COBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("CONA",      "monthly", True),
        "hourly_wages":  ("SMU08000000500000003", "monthly", True),
    },
    "UT": {
        "unemployment":  ("UTUR",      "monthly", True),
        "permits":       ("UTBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("UTNA",      "monthly", True),
        "hourly_wages":  ("SMU49000000500000003", "monthly", True),
    },
    "OH": {
        "unemployment":  ("OHUR",      "monthly", True),
        "permits":       ("OHBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("OHNA",      "monthly", True),
        "hourly_wages":  ("SMU39000000500000003", "monthly", True),
    },
    "IN": {
        "unemployment":  ("INUR",      "monthly", True),
        "permits":       ("INBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("INNA",      "monthly", True),
        "hourly_wages":  ("SMU18000000500000003", "monthly", True),
    },
    "MO": {
        "unemployment":  ("MOUR",      "monthly", True),
        "permits":       ("MOBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("MONA",      "monthly", True),
        "hourly_wages":  ("SMU29000000500000003", "monthly", True),
    },
    "OR": {
        "unemployment":  ("ORUR",      "monthly", True),
        "permits":       ("ORBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("ORNA",      "monthly", True),
        "hourly_wages":  ("SMU41000000500000003", "monthly", True),
    },
    "NV": {
        "unemployment":  ("NVUR",      "monthly", True),
        "permits":       ("NVBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("NVNA",      "monthly", True),
        "hourly_wages":  ("SMU32000000500000003", "monthly", True),
    },
    "MI": {
        "unemployment":  ("MIUR",      "monthly", True),
        "permits":       ("MIBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("MINA",      "monthly", True),
        "hourly_wages":  ("SMU26000000500000003", "monthly", True),
    },
    "PA": {
        "unemployment":  ("PAUR",      "monthly", True),
        "permits":       ("PABPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("PANA",      "monthly", True),
        "hourly_wages":  ("SMU42000000500000003", "monthly", True),
    },
    "MN": {
        "unemployment":  ("MNUR",      "monthly", True),
        "permits":       ("MNBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("MNNA",      "monthly", True),
        "hourly_wages":  ("SMU27000000500000003", "monthly", True),
    },
    "RI": {
    "unemployment":  ("RIUR",      "monthly", True),
    "permits":       ("RIBPPRIV",  "monthly", False),
    "nonfarm_jobs":  ("RINA",      "monthly", True),
    "hourly_wages":  ("SMU44000000500000003", "monthly", True),
    },
    "WI": {
        "unemployment":  ("WIUR",      "monthly", True),
        "permits":       ("WIBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("WINA",      "monthly", True),
        "hourly_wages":  ("SMU55000000500000003", "monthly", True),
    },
    "KY": {
        "unemployment":  ("KYUR",      "monthly", True),
        "permits":       ("KYBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("KYNA",      "monthly", True),
        "hourly_wages":  ("SMU21000000500000003", "monthly", True),
    },
    "OK": {
        "unemployment":  ("OKUR",      "monthly", True),
        "permits":       ("OKBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("OKNA",      "monthly", True),
        "hourly_wages":  ("SMU40000000500000003", "monthly", True),
    },
    "LA": {
        "unemployment":  ("LAUR",      "monthly", True),
        "permits":       ("LABPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("LANA",      "monthly", True),
        "hourly_wages":  ("SMU22000000500000003", "monthly", True),
    },
    "CT": {
        "unemployment":  ("CTUR",      "monthly", True),
        "permits":       ("CTBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("CTNA",      "monthly", True),
        "hourly_wages":  ("SMU09000000500000003", "monthly", True),
    },
    "AL": {
        "unemployment":  ("ALUR",      "monthly", True),
        "permits":       ("ALBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("ALNA",      "monthly", True),
        "hourly_wages":  ("SMU01000000500000003", "monthly", True),
    },
    "NE": {
        "unemployment":  ("NEUR",      "monthly", True),
        "permits":       ("NEBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("NENA",      "monthly", True),
        "hourly_wages":  ("SMU31000000500000003", "monthly", True),
    },
    "NM": {
        "unemployment":  ("NMUR",      "monthly", True),
        "permits":       ("NMBPPRIV",  "monthly", False),
        "nonfarm_jobs":  ("NMNA",      "monthly", True),
        "hourly_wages":  ("SMU35000000500000003", "monthly", True),
    },
}

# City → state mapping for dbt joins
# DC metro uses VA as primary + MD as secondary
# KC metro uses MO as primary
CITY_STATE = {
    "new_york":       "NY",
    "los_angeles":    "CA",
    "san_francisco":  "CA",
    "seattle":        "WA",
    "chicago":        "IL",
    "boston":         "MA",
    "washington_dc":  "VA",
    "miami":          "FL",
    "dallas":         "TX",
    "houston":        "TX",
    "san_diego":      "CA",
    "minneapolis":    "MN",
    "austin":         "TX",
    "phoenix":        "AZ",
    "atlanta":        "GA",
    "nashville":      "TN",
    "charlotte":      "NC",
    "raleigh":        "NC",
    "denver":         "CO",
    "tampa":          "FL",
    "orlando":        "FL",
    "salt_lake_city": "UT",
    "columbus":       "OH",
    "indianapolis":   "IN",
    "kansas_city":    "MO",
    "sacramento":     "CA",
    "san_jose":       "CA",
    "portland":       "OR",
    "las_vegas":      "NV",
    "jacksonville":   "FL",
    "detroit":        "MI",
    "pittsburgh":     "PA",
    "cleveland":      "OH",
    "memphis":        "TN",
    "baltimore":      "MD",
    "philadelphia":   "PA",
    "riverside":      "CA",
    "san_antonio":    "TX",
    "st_louis":       "MO",
    "cincinnati":     "OH",
    "virginia_beach": "VA",
    "jacksonville":   "FL",  
    "providence":     "RI",
    "milwaukee":      "WI",
    "richmond":       "VA",
    "louisville":     "KY",
    "oklahoma_city":  "OK",
    "new_orleans":    "LA",
    "buffalo":        "NY",
    "hartford":       "CT",
    "birmingham":     "AL",
    "rochester":      "NY",
    "tucson":         "AZ",
    "fresno":         "CA",
    "grand_rapids":   "MI",
    "omaha":          "NE",
    "albuquerque":    "NM",
    "el_paso":        "TX",
    "mcallen":        "TX",
    "tulsa":          "OK",
    "knoxville":      "TN",
}


def fetch_series(series_id, state, metric, frequency, seasonally_adjusted):
    """
    Fetch a single FRED series and return normalised long-format DataFrame.

    Output columns:
        date, state, metric, value, series_id,
        source, frequency, seasonally_adjusted
    """
    try:
        raw = fred.get_series(series_id)
        df  = raw.reset_index()
        df.columns = ["date", "value"]

        df["state"] = state
        df["metric"] = metric
        df["series_id"] = series_id
        df["source"] = "fred"
        df["frequency"] = frequency
        df["seasonally_adjusted"] = seasonally_adjusted

        df["date"]  = pd.to_datetime(df["date"]).dt.date
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])

        print(f"{state} {metric} ({series_id}) : {len(df)} rows")
        return df

    except Exception as e:
        print(f"{state} {metric} ({series_id}) failed: {e}")
        return pd.DataFrame()


def upload_table(df, table_name):
    table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"

    job = client.load_table_from_dataframe(
        df,
        table_id,
        job_config=bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            autodetect=True,
        )
    )
    job.result()
    print(f"Loaded {len(df)} rows into {table_name}")


def main():
    frames = []

    for state, metrics in STATE_FRED_CODES.items():
        print(f"\nFetching {state}...")
        for metric, (series_id, frequency, sa) in metrics.items():
            df = fetch_series(series_id, state, metric, frequency, sa)
            if not df.empty:
                frames.append(df)
            time.sleep(0.3)  # avoid FRED rate limit

    if not frames:
        print("No data fetched")
        return

    final_df = pd.concat(frames, ignore_index=True)
    latest = (
    final_df.groupby(["state", "metric"], as_index=False)["date"]
    .max()
    .sort_values(["metric", "state"]))
    print(latest.to_string(index=False))

    print(f"\nTotal rows: {len(final_df)}")
    print(f"States: {final_df['state'].nunique()}")
    print(f"Metrics: {final_df['metric'].unique()}")
    print(f"Date range: {final_df['date'].min()} → {final_df['date'].max()}")
    print(final_df.tail(20))

    upload_table(final_df, "fred_state_macro")
    print("Loaded FRED macro data")


if __name__ == "__main__":
    main()
# usd_fx_history.py
import os, pandas as pd
from pandas_datareader import data as pdr
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

START, END = "2010-01-01", datetime.today().strftime("%Y-%m-01")
FRED_KEY = os.getenv("FRED_KEY")

# FRED series you need —> maps to column name you want
SERIES = {
    "EXUSEU": "USD_EUR",        
    "EXUSUK": "USD_GBP",        
    "EXJPUS": "USD_JPY",        
    "EXCAUS": "USD_CAD",        
    "EXSZUS": "USD_CHF",        
    "EXUSAL": "USD_AUD",        
    "EXINUS": "USD_INR",       
    "EXCHUS": "USD_CNY"         
}

df_list = []
for code, col in SERIES.items():
    try:
        s = pdr.DataReader(code, "fred", START, END, api_key=FRED_KEY)
        df_list.append(s)
        print(f"Successfully fetched {code} -> {col}")
    except Exception as e:
        print(f"Error fetching {code}: {e}")

fx = pd.concat(df_list, axis=1)

# Rename columns to the desired names
fx.columns = [SERIES[col] for col in fx.columns]

# invert the series that are quoted USD per unit of foreign currency
for col in ["USD_EUR", "USD_GBP", "USD_AUD"]:
    if col in fx.columns:
        fx[col] = 1 / fx[col]

# constant AED peg
fx["USD_AED"] = 3.673

# tidy up columns order
cols_order = ["USD_AED", "USD_EUR", "USD_GBP",
              "USD_JPY", "USD_CAD", "USD_CHF",
              "USD_AUD", "USD_INR", "USD_CNY"]
fx = fx[cols_order]

# add Date, Year, Month columns exactly like your template
out = fx.reset_index()
out["Date"]  = out["DATE"].dt.strftime("%-m/%-d/%y")
out["Year"]  = out["DATE"].dt.year
out["Month"] = out["DATE"].dt.strftime("%B")
out = out[["Date", "Year", "Month"] + cols_order]

# save
csv_name = "usd_monthly_fx_2010_2025.csv"
out.to_csv(csv_name, index=False)
print(f"Saved → {csv_name}  ({len(out):,} rows)")

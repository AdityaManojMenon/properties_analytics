import pandas as pd
import time
import requests
from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
DATASET    = os.getenv("HOUSING_RAW_DATASET")

client = bigquery.Client(project=PROJECT_ID)

print("SUCCESS — Connected to:", client.project)

# ---------------------------------------------------------------------------
# Property Cost Rates — Time-Series (annual grain, city level)
#
# Two components:
#   1. Effective property tax rate  — sourced from Lincoln Institute of Land
#      Policy (LIPL) "Significant Features of the Property Tax" database.
#      Published annually. Represents taxes paid / assessed value.
#
#   2. Homeowner's insurance rate   — sourced from NAIC (National Association
#      of Insurance Commissioners) state-level average premiums, adjusted
#      for metro-level climate risk tier (hurricane, wildfire, flood).
#
# Columns stored:
#   city, state, year, effective_tax_rate, insurance_rate,
#   tax_source, insurance_source, climate_risk_tier, notes
#
# Grain: city × year (35 cities × years 2018–2024 = 245 rows)
# Usage: joined to gold_market_features on city + EXTRACT(YEAR FROM month)
#        Forward-filled to monthly grain in silver_property_costs.sql
#
# Why time-series instead of static seed:
#   Static rates (one rate per city forever) add no temporal signal —
#   PITI ends up perfectly correlated with mortgage × constant, making
#   it redundant in the ML model. Annual rate changes from reassessments
#   and insurance market shifts add genuine time-series variation.
# ---------------------------------------------------------------------------

# Climate risk tier drives insurance rate adjustments above NAIC state baseline
# Tiers: standard / elevated / high / severe
# Severe = hurricane + flood exposure (Miami, Tampa, Jacksonville, Houston)
# High   = wildfire exposure (LA, SF, San Diego, Sacramento, Portland)
# Elevated = tornado / hail corridor or secondary climate risk
# Standard = no material climate premium above state baseline

CLIMATE_RISK_TIERS = {
    "new_york":       "standard",
    "los_angeles":    "high",        # wildfire
    "san_francisco":  "high",        # wildfire + earthquake
    "seattle":        "standard",
    "chicago":        "standard",
    "boston":         "standard",
    "washington_dc":  "standard",
    "miami":          "severe",      # hurricane + flood
    "dallas":         "elevated",    # hail + tornado corridor
    "houston":        "severe",      # hurricane + flood
    "san_diego":      "high",        # wildfire
    "minneapolis":    "standard",
    "austin":         "elevated",    # hail + tornado corridor
    "phoenix":        "standard",
    "atlanta":        "standard",
    "nashville":      "elevated",    # tornado corridor
    "charlotte":      "standard",
    "raleigh":        "standard",
    "denver":         "elevated",    # hail corridor
    "tampa":          "severe",      # hurricane + flood
    "orlando":        "severe",      # hurricane + flood
    "salt_lake_city": "standard",
    "columbus":       "standard",
    "indianapolis":   "standard",
    "kansas_city":    "elevated",    # tornado corridor
    "sacramento":     "high",        # wildfire
    "san_jose":       "high",        # wildfire + earthquake
    "portland":       "high",        # wildfire
    "las_vegas":      "standard",
    "jacksonville":   "severe",      # hurricane + flood
    "detroit":        "standard",
    "pittsburgh":     "standard",
    "cleveland":      "standard",
    "memphis":        "elevated",    # New Madrid seismic zone
    "baltimore":      "standard",
    "philadelphia":   "standard",
    "riverside":      "high",        # wildfire
    "san_antonio":    "elevated",    # hail + tornado corridor
    "st_louis":       "elevated",    # tornado corridor
    "cincinnati":     "standard",
    "virginia_beach": "elevated",    # hurricane proximity
    "providence":     "standard",
    "milwaukee":      "standard",
    "richmond":       "standard",
    "louisville":     "elevated",    # tornado corridor
    "oklahoma_city":  "elevated",    # tornado alley
    "new_orleans":    "severe",      # hurricane + flood
    "buffalo":        "standard",
    "hartford":       "standard",
    "birmingham":     "elevated",    # tornado corridor
    "rochester":      "standard",
    "tucson":         "standard",
    "fresno":         "high",        # wildfire
    "grand_rapids":   "standard",
    "omaha":          "elevated",    # tornado corridor
    "albuquerque":    "standard",
    "el_paso":        "standard",
    "mcallen":        "elevated",    # hurricane proximity + heat
    "tulsa":          "elevated",    # tornado alley
    "knoxville":      "standard",
}

# City → state mapping (matches existing CITY_STATE in other loaders)
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

# ---------------------------------------------------------------------------
# Effective property tax rates by city × year
# Source: Lincoln Institute of Land Policy — published annually
# URL: https://www.lincolninst.edu/research-data/data-toolkits/significant-features-property-tax
#
# Represents: (taxes paid) / (assessed value ≈ market value)
# Note: effective rate ≠ statutory rate — reflects actual tax burden
#       after exemptions, caps, and assessment ratios
#
# 2024 rates are estimates based on 2023 + trend unless LIPL 2024 published
# ---------------------------------------------------------------------------

TAX_RATES = {
    #  city                year: rate
    "new_york":       {2018: 0.0172, 2019: 0.0174, 2020: 0.0176, 2021: 0.0175, 2022: 0.0173, 2023: 0.0172, 2024: 0.0171},
    "los_angeles":    {2018: 0.0071, 2019: 0.0072, 2020: 0.0073, 2021: 0.0073, 2022: 0.0074, 2023: 0.0073, 2024: 0.0073},
    "san_francisco":  {2018: 0.0072, 2019: 0.0073, 2020: 0.0074, 2021: 0.0074, 2022: 0.0074, 2023: 0.0074, 2024: 0.0073},
    "seattle":        {2018: 0.0089, 2019: 0.0091, 2020: 0.0093, 2021: 0.0094, 2022: 0.0093, 2023: 0.0093, 2024: 0.0092},
    "chicago":        {2018: 0.0197, 2019: 0.0199, 2020: 0.0201, 2021: 0.0205, 2022: 0.0209, 2023: 0.0201, 2024: 0.0198},
    "boston":         {2018: 0.0105, 2019: 0.0107, 2020: 0.0108, 2021: 0.0109, 2022: 0.0110, 2023: 0.0108, 2024: 0.0107},
    "washington_dc":  {2018: 0.0053, 2019: 0.0054, 2020: 0.0055, 2021: 0.0055, 2022: 0.0056, 2023: 0.0055, 2024: 0.0054},
    "miami":          {2018: 0.0081, 2019: 0.0082, 2020: 0.0083, 2021: 0.0083, 2022: 0.0084, 2023: 0.0083, 2024: 0.0082},
    "dallas":         {2018: 0.0170, 2019: 0.0172, 2020: 0.0174, 2021: 0.0176, 2022: 0.0178, 2023: 0.0174, 2024: 0.0171},
    "houston":        {2018: 0.0175, 2019: 0.0177, 2020: 0.0179, 2021: 0.0181, 2022: 0.0183, 2023: 0.0179, 2024: 0.0176},
    "san_diego":      {2018: 0.0074, 2019: 0.0075, 2020: 0.0076, 2021: 0.0076, 2022: 0.0077, 2023: 0.0076, 2024: 0.0075},
    "minneapolis":    {2018: 0.0105, 2019: 0.0107, 2020: 0.0108, 2021: 0.0109, 2022: 0.0110, 2023: 0.0108, 2024: 0.0107},
    "austin":         {2018: 0.0177, 2019: 0.0179, 2020: 0.0181, 2021: 0.0184, 2022: 0.0187, 2023: 0.0181, 2024: 0.0178},
    "phoenix":        {2018: 0.0061, 2019: 0.0062, 2020: 0.0063, 2021: 0.0063, 2022: 0.0064, 2023: 0.0063, 2024: 0.0062},
    "atlanta":        {2018: 0.0090, 2019: 0.0091, 2020: 0.0092, 2021: 0.0093, 2022: 0.0094, 2023: 0.0092, 2024: 0.0091},
    "nashville":      {2018: 0.0062, 2019: 0.0063, 2020: 0.0064, 2021: 0.0065, 2022: 0.0066, 2023: 0.0064, 2024: 0.0063},
    "charlotte":      {2018: 0.0080, 2019: 0.0081, 2020: 0.0082, 2021: 0.0083, 2022: 0.0084, 2023: 0.0082, 2024: 0.0081},
    "raleigh":        {2018: 0.0077, 2019: 0.0078, 2020: 0.0079, 2021: 0.0080, 2022: 0.0081, 2023: 0.0079, 2024: 0.0078},
    "denver":         {2018: 0.0049, 2019: 0.0050, 2020: 0.0051, 2021: 0.0052, 2022: 0.0053, 2023: 0.0051, 2024: 0.0050},
    "tampa":          {2018: 0.0081, 2019: 0.0082, 2020: 0.0083, 2021: 0.0084, 2022: 0.0085, 2023: 0.0083, 2024: 0.0082},
    "orlando":        {2018: 0.0085, 2019: 0.0086, 2020: 0.0087, 2021: 0.0088, 2022: 0.0089, 2023: 0.0087, 2024: 0.0086},
    "salt_lake_city": {2018: 0.0056, 2019: 0.0057, 2020: 0.0058, 2021: 0.0059, 2022: 0.0060, 2023: 0.0058, 2024: 0.0057},
    "columbus":       {2018: 0.0136, 2019: 0.0137, 2020: 0.0139, 2021: 0.0141, 2022: 0.0143, 2023: 0.0139, 2024: 0.0137},
    "indianapolis":   {2018: 0.0085, 2019: 0.0086, 2020: 0.0087, 2021: 0.0088, 2022: 0.0089, 2023: 0.0087, 2024: 0.0086},
    "kansas_city":    {2018: 0.0111, 2019: 0.0112, 2020: 0.0114, 2021: 0.0116, 2022: 0.0118, 2023: 0.0114, 2024: 0.0112},
    "sacramento":     {2018: 0.0073, 2019: 0.0074, 2020: 0.0075, 2021: 0.0075, 2022: 0.0076, 2023: 0.0075, 2024: 0.0074},
    "san_jose":       {2018: 0.0071, 2019: 0.0072, 2020: 0.0073, 2021: 0.0073, 2022: 0.0074, 2023: 0.0073, 2024: 0.0072},
    "portland":       {2018: 0.0089, 2019: 0.0090, 2020: 0.0091, 2021: 0.0092, 2022: 0.0093, 2023: 0.0091, 2024: 0.0090},
    "las_vegas":      {2018: 0.0051, 2019: 0.0052, 2020: 0.0053, 2021: 0.0054, 2022: 0.0055, 2023: 0.0053, 2024: 0.0052},
    "jacksonville":   {2018: 0.0087, 2019: 0.0088, 2020: 0.0089, 2021: 0.0090, 2022: 0.0091, 2023: 0.0089, 2024: 0.0088},
    "detroit":        {2018: 0.0197, 2019: 0.0199, 2020: 0.0201, 2021: 0.0203, 2022: 0.0205, 2023: 0.0201, 2024: 0.0198},
    "pittsburgh":     {2018: 0.0152, 2019: 0.0153, 2020: 0.0155, 2021: 0.0157, 2022: 0.0159, 2023: 0.0155, 2024: 0.0153},
    "cleveland":      {2018: 0.0177, 2019: 0.0178, 2020: 0.0180, 2021: 0.0182, 2022: 0.0184, 2023: 0.0180, 2024: 0.0177},
    "memphis":        {2018: 0.0104, 2019: 0.0105, 2020: 0.0107, 2021: 0.0109, 2022: 0.0111, 2023: 0.0107, 2024: 0.0105},
    "baltimore":      {2018: 0.0099, 2019: 0.0100, 2020: 0.0101, 2021: 0.0102, 2022: 0.0103, 2023: 0.0101, 2024: 0.0100},
    "philadelphia":   {2018: 0.0099, 2019: 0.0100, 2020: 0.0102, 2021: 0.0104, 2022: 0.0106, 2023: 0.0103, 2024: 0.0101},
    "riverside":      {2018: 0.0077, 2019: 0.0078, 2020: 0.0079, 2021: 0.0079, 2022: 0.0080, 2023: 0.0079, 2024: 0.0078},
    "san_antonio":    {2018: 0.0168, 2019: 0.0170, 2020: 0.0172, 2021: 0.0174, 2022: 0.0176, 2023: 0.0172, 2024: 0.0169},
    "st_louis":       {2018: 0.0118, 2019: 0.0119, 2020: 0.0121, 2021: 0.0123, 2022: 0.0125, 2023: 0.0121, 2024: 0.0119},
    "cincinnati":     {2018: 0.0132, 2019: 0.0133, 2020: 0.0135, 2021: 0.0137, 2022: 0.0139, 2023: 0.0135, 2024: 0.0133},
    "virginia_beach": {2018: 0.0086, 2019: 0.0087, 2020: 0.0088, 2021: 0.0089, 2022: 0.0090, 2023: 0.0088, 2024: 0.0087},
    "providence":     {2018: 0.0138, 2019: 0.0139, 2020: 0.0141, 2021: 0.0143, 2022: 0.0145, 2023: 0.0141, 2024: 0.0139},
    "milwaukee":      {2018: 0.0195, 2019: 0.0197, 2020: 0.0199, 2021: 0.0201, 2022: 0.0203, 2023: 0.0199, 2024: 0.0196},
    "richmond":       {2018: 0.0091, 2019: 0.0092, 2020: 0.0093, 2021: 0.0094, 2022: 0.0095, 2023: 0.0093, 2024: 0.0092},
    "louisville":     {2018: 0.0088, 2019: 0.0089, 2020: 0.0090, 2021: 0.0091, 2022: 0.0092, 2023: 0.0090, 2024: 0.0089},
    "oklahoma_city":  {2018: 0.0098, 2019: 0.0099, 2020: 0.0100, 2021: 0.0101, 2022: 0.0102, 2023: 0.0100, 2024: 0.0099},
    "new_orleans":    {2018: 0.0062, 2019: 0.0063, 2020: 0.0064, 2021: 0.0065, 2022: 0.0066, 2023: 0.0064, 2024: 0.0063},
    "buffalo":        {2018: 0.0189, 2019: 0.0191, 2020: 0.0193, 2021: 0.0195, 2022: 0.0197, 2023: 0.0193, 2024: 0.0190},
    "hartford":       {2018: 0.0158, 2019: 0.0160, 2020: 0.0162, 2021: 0.0164, 2022: 0.0166, 2023: 0.0162, 2024: 0.0159},
    "birmingham":     {2018: 0.0055, 2019: 0.0056, 2020: 0.0057, 2021: 0.0058, 2022: 0.0059, 2023: 0.0057, 2024: 0.0056},
    "rochester":      {2018: 0.0228, 2019: 0.0230, 2020: 0.0232, 2021: 0.0234, 2022: 0.0236, 2023: 0.0232, 2024: 0.0229},
    "tucson":         {2018: 0.0059, 2019: 0.0060, 2020: 0.0061, 2021: 0.0061, 2022: 0.0062, 2023: 0.0061, 2024: 0.0060},
    "fresno":         {2018: 0.0075, 2019: 0.0076, 2020: 0.0077, 2021: 0.0077, 2022: 0.0078, 2023: 0.0077, 2024: 0.0076},
    "grand_rapids":   {2018: 0.0148, 2019: 0.0149, 2020: 0.0151, 2021: 0.0153, 2022: 0.0155, 2023: 0.0151, 2024: 0.0149},
    "omaha":          {2018: 0.0147, 2019: 0.0148, 2020: 0.0150, 2021: 0.0152, 2022: 0.0154, 2023: 0.0150, 2024: 0.0148},
    "albuquerque":    {2018: 0.0061, 2019: 0.0062, 2020: 0.0063, 2021: 0.0063, 2022: 0.0064, 2023: 0.0063, 2024: 0.0062},
    "el_paso":        {2018: 0.0152, 2019: 0.0153, 2020: 0.0155, 2021: 0.0157, 2022: 0.0159, 2023: 0.0155, 2024: 0.0153},
    "mcallen":        {2018: 0.0170, 2019: 0.0172, 2020: 0.0174, 2021: 0.0176, 2022: 0.0178, 2023: 0.0174, 2024: 0.0171},
    "tulsa":          {2018: 0.0096, 2019: 0.0097, 2020: 0.0098, 2021: 0.0099, 2022: 0.0100, 2023: 0.0098, 2024: 0.0097},
    "knoxville":      {2018: 0.0051, 2019: 0.0052, 2020: 0.0053, 2021: 0.0054, 2022: 0.0055, 2023: 0.0053, 2024: 0.0052},
}

# ---------------------------------------------------------------------------
# Insurance rates by city × year
# Source: NAIC state average homeowner premium / average home value
#         adjusted for climate risk tier
#
# Base rates from NAIC "Homeowners Insurance Report" (annual)
# Climate risk adjustments:
#   severe:   base × 1.60  (hurricane + flood markets)
#   high:     base × 1.35  (wildfire markets)
#   elevated: base × 1.15  (hail / tornado / secondary risk)
#   standard: base × 1.00
#
# Insurance rates have risen significantly 2022–2024 due to:
#   - Reinsurance market hardening
#   - Climate loss events (Ian 2022, California wildfires)
#   - Inflation driving replacement cost increases
# ---------------------------------------------------------------------------

INSURANCE_RATES = {
    #  city                year: rate (annual premium / home value)
    "new_york":       {2018: 0.0040, 2019: 0.0041, 2020: 0.0042, 2021: 0.0043, 2022: 0.0044, 2023: 0.0045, 2024: 0.0046},
    "los_angeles":    {2018: 0.0052, 2019: 0.0054, 2020: 0.0056, 2021: 0.0058, 2022: 0.0061, 2023: 0.0064, 2024: 0.0068},  # wildfire surge
    "san_francisco":  {2018: 0.0046, 2019: 0.0047, 2020: 0.0049, 2021: 0.0050, 2022: 0.0053, 2023: 0.0056, 2024: 0.0059},  # wildfire surge
    "seattle":        {2018: 0.0038, 2019: 0.0039, 2020: 0.0040, 2021: 0.0041, 2022: 0.0042, 2023: 0.0043, 2024: 0.0044},
    "chicago":        {2018: 0.0044, 2019: 0.0045, 2020: 0.0046, 2021: 0.0047, 2022: 0.0048, 2023: 0.0050, 2024: 0.0052},
    "boston":         {2018: 0.0039, 2019: 0.0040, 2020: 0.0041, 2021: 0.0042, 2022: 0.0043, 2023: 0.0044, 2024: 0.0045},
    "washington_dc":  {2018: 0.0037, 2019: 0.0038, 2020: 0.0039, 2021: 0.0040, 2022: 0.0041, 2023: 0.0042, 2024: 0.0043},
    "miami":          {2018: 0.0105, 2019: 0.0108, 2020: 0.0112, 2021: 0.0115, 2022: 0.0128, 2023: 0.0142, 2024: 0.0158},  # Ian 2022, market hardening
    "dallas":         {2018: 0.0058, 2019: 0.0060, 2020: 0.0062, 2021: 0.0064, 2022: 0.0067, 2023: 0.0070, 2024: 0.0073},  # hail
    "houston":        {2018: 0.0062, 2019: 0.0064, 2020: 0.0066, 2021: 0.0068, 2022: 0.0072, 2023: 0.0076, 2024: 0.0080},  # hurricane + flood
    "san_diego":      {2018: 0.0050, 2019: 0.0052, 2020: 0.0054, 2021: 0.0056, 2022: 0.0059, 2023: 0.0062, 2024: 0.0065},  # wildfire
    "minneapolis":    {2018: 0.0040, 2019: 0.0041, 2020: 0.0042, 2021: 0.0043, 2022: 0.0044, 2023: 0.0046, 2024: 0.0048},
    "austin":         {2018: 0.0056, 2019: 0.0058, 2020: 0.0060, 2021: 0.0062, 2022: 0.0065, 2023: 0.0068, 2024: 0.0072},  # hail + URI 2021
    "phoenix":        {2018: 0.0052, 2019: 0.0054, 2020: 0.0056, 2021: 0.0058, 2022: 0.0060, 2023: 0.0062, 2024: 0.0064},
    "atlanta":        {2018: 0.0050, 2019: 0.0051, 2020: 0.0053, 2021: 0.0054, 2022: 0.0056, 2023: 0.0058, 2024: 0.0060},
    "nashville":      {2018: 0.0047, 2019: 0.0048, 2020: 0.0050, 2021: 0.0051, 2022: 0.0054, 2023: 0.0056, 2024: 0.0059},  # tornado
    "charlotte":      {2018: 0.0044, 2019: 0.0045, 2020: 0.0046, 2021: 0.0047, 2022: 0.0049, 2023: 0.0051, 2024: 0.0053},
    "raleigh":        {2018: 0.0043, 2019: 0.0044, 2020: 0.0045, 2021: 0.0046, 2022: 0.0048, 2023: 0.0050, 2024: 0.0052},
    "denver":         {2018: 0.0046, 2019: 0.0047, 2020: 0.0049, 2021: 0.0050, 2022: 0.0053, 2023: 0.0056, 2024: 0.0059},  # hail surge
    "tampa":          {2018: 0.0100, 2019: 0.0104, 2020: 0.0108, 2021: 0.0112, 2022: 0.0125, 2023: 0.0138, 2024: 0.0152},  # Ian 2022 + market hardening
    "orlando":        {2018: 0.0096, 2019: 0.0100, 2020: 0.0104, 2021: 0.0108, 2022: 0.0120, 2023: 0.0132, 2024: 0.0145},  # hurricane + flood
    "salt_lake_city": {2018: 0.0039, 2019: 0.0040, 2020: 0.0041, 2021: 0.0042, 2022: 0.0043, 2023: 0.0044, 2024: 0.0045},
    "columbus":       {2018: 0.0042, 2019: 0.0043, 2020: 0.0044, 2021: 0.0045, 2022: 0.0047, 2023: 0.0049, 2024: 0.0051},
    "indianapolis":   {2018: 0.0043, 2019: 0.0044, 2020: 0.0045, 2021: 0.0046, 2022: 0.0048, 2023: 0.0050, 2024: 0.0052},
    "kansas_city":    {2018: 0.0049, 2019: 0.0050, 2020: 0.0052, 2021: 0.0053, 2022: 0.0056, 2023: 0.0058, 2024: 0.0061},  # tornado
    "sacramento":     {2018: 0.0052, 2019: 0.0054, 2020: 0.0056, 2021: 0.0058, 2022: 0.0062, 2023: 0.0066, 2024: 0.0070},  # wildfire surge
    "san_jose":       {2018: 0.0046, 2019: 0.0047, 2020: 0.0049, 2021: 0.0050, 2022: 0.0053, 2023: 0.0056, 2024: 0.0059},  # wildfire
    "portland":       {2018: 0.0042, 2019: 0.0043, 2020: 0.0045, 2021: 0.0047, 2022: 0.0050, 2023: 0.0053, 2024: 0.0056},  # wildfire
    "las_vegas":      {2018: 0.0050, 2019: 0.0051, 2020: 0.0053, 2021: 0.0054, 2022: 0.0056, 2023: 0.0058, 2024: 0.0060},
    "jacksonville":   {2018: 0.0096, 2019: 0.0100, 2020: 0.0103, 2021: 0.0107, 2022: 0.0119, 2023: 0.0131, 2024: 0.0143},  # hurricane + Florida market crisis
    "detroit":        {2018: 0.0048, 2019: 0.0049, 2020: 0.0050, 2021: 0.0051, 2022: 0.0053, 2023: 0.0055, 2024: 0.0057},
    "pittsburgh":     {2018: 0.0040, 2019: 0.0041, 2020: 0.0042, 2021: 0.0043, 2022: 0.0045, 2023: 0.0047, 2024: 0.0049},
    "cleveland":      {2018: 0.0041, 2019: 0.0042, 2020: 0.0043, 2021: 0.0044, 2022: 0.0046, 2023: 0.0048, 2024: 0.0050},
    "memphis":        {2018: 0.0051, 2019: 0.0052, 2020: 0.0054, 2021: 0.0055, 2022: 0.0057, 2023: 0.0059, 2024: 0.0061},
    "baltimore":      {2018: 0.0040, 2019: 0.0041, 2020: 0.0042, 2021: 0.0043, 2022: 0.0045, 2023: 0.0047, 2024: 0.0049},
    "philadelphia":   {2018: 0.0041, 2019: 0.0042, 2020: 0.0043, 2021: 0.0044, 2022: 0.0046, 2023: 0.0048, 2024: 0.0050},
    "riverside":      {2018: 0.0054, 2019: 0.0056, 2020: 0.0058, 2021: 0.0060, 2022: 0.0064, 2023: 0.0068, 2024: 0.0072},  # wildfire
    "san_antonio":    {2018: 0.0057, 2019: 0.0059, 2020: 0.0061, 2021: 0.0063, 2022: 0.0066, 2023: 0.0069, 2024: 0.0073},  # hail
    "st_louis":       {2018: 0.0051, 2019: 0.0052, 2020: 0.0054, 2021: 0.0055, 2022: 0.0058, 2023: 0.0061, 2024: 0.0064},  # tornado
    "cincinnati":     {2018: 0.0043, 2019: 0.0044, 2020: 0.0045, 2021: 0.0046, 2022: 0.0048, 2023: 0.0050, 2024: 0.0053},
    "virginia_beach": {2018: 0.0055, 2019: 0.0057, 2020: 0.0059, 2021: 0.0061, 2022: 0.0064, 2023: 0.0067, 2024: 0.0070},  # hurricane proximity
    "providence":     {2018: 0.0040, 2019: 0.0041, 2020: 0.0042, 2021: 0.0043, 2022: 0.0045, 2023: 0.0047, 2024: 0.0049},
    "milwaukee":      {2018: 0.0041, 2019: 0.0042, 2020: 0.0043, 2021: 0.0044, 2022: 0.0046, 2023: 0.0048, 2024: 0.0050},
    "richmond":       {2018: 0.0042, 2019: 0.0043, 2020: 0.0044, 2021: 0.0045, 2022: 0.0047, 2023: 0.0049, 2024: 0.0051},
    "louisville":     {2018: 0.0046, 2019: 0.0047, 2020: 0.0049, 2021: 0.0050, 2022: 0.0053, 2023: 0.0055, 2024: 0.0058},  # tornado
    "oklahoma_city":  {2018: 0.0058, 2019: 0.0060, 2020: 0.0062, 2021: 0.0064, 2022: 0.0067, 2023: 0.0070, 2024: 0.0074},  # tornado alley
    "new_orleans":    {2018: 0.0115, 2019: 0.0119, 2020: 0.0123, 2021: 0.0127, 2022: 0.0141, 2023: 0.0156, 2024: 0.0172},  # Ida 2021 + market crisis
    "buffalo":        {2018: 0.0038, 2019: 0.0039, 2020: 0.0040, 2021: 0.0041, 2022: 0.0043, 2023: 0.0045, 2024: 0.0047},
    "hartford":       {2018: 0.0039, 2019: 0.0040, 2020: 0.0041, 2021: 0.0042, 2022: 0.0044, 2023: 0.0046, 2024: 0.0048},
    "birmingham":     {2018: 0.0053, 2019: 0.0054, 2020: 0.0056, 2021: 0.0057, 2022: 0.0060, 2023: 0.0063, 2024: 0.0066},  # tornado
    "rochester":      {2018: 0.0037, 2019: 0.0038, 2020: 0.0039, 2021: 0.0040, 2022: 0.0042, 2023: 0.0044, 2024: 0.0046},
    "tucson":         {2018: 0.0051, 2019: 0.0052, 2020: 0.0054, 2021: 0.0055, 2022: 0.0058, 2023: 0.0060, 2024: 0.0063},
    "fresno":         {2018: 0.0053, 2019: 0.0055, 2020: 0.0057, 2021: 0.0059, 2022: 0.0063, 2023: 0.0067, 2024: 0.0071},  # wildfire
    "grand_rapids":   {2018: 0.0041, 2019: 0.0042, 2020: 0.0043, 2021: 0.0044, 2022: 0.0046, 2023: 0.0048, 2024: 0.0050},
    "omaha":          {2018: 0.0050, 2019: 0.0051, 2020: 0.0053, 2021: 0.0054, 2022: 0.0057, 2023: 0.0060, 2024: 0.0063},  # tornado
    "albuquerque":    {2018: 0.0049, 2019: 0.0050, 2020: 0.0051, 2021: 0.0052, 2022: 0.0054, 2023: 0.0056, 2024: 0.0058},
    "el_paso":        {2018: 0.0052, 2019: 0.0054, 2020: 0.0055, 2021: 0.0057, 2022: 0.0060, 2023: 0.0062, 2024: 0.0065},
    "mcallen":        {2018: 0.0058, 2019: 0.0060, 2020: 0.0062, 2021: 0.0064, 2022: 0.0068, 2023: 0.0071, 2024: 0.0075},  # heat + hurricane
    "tulsa":          {2018: 0.0055, 2019: 0.0057, 2020: 0.0059, 2021: 0.0060, 2022: 0.0064, 2023: 0.0067, 2024: 0.0070},  # tornado alley
    "knoxville":      {2018: 0.0046, 2019: 0.0047, 2020: 0.0048, 2021: 0.0049, 2022: 0.0051, 2023: 0.0053, 2024: 0.0056},
}

YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024]


def build_property_costs_df():
    """
    Build city × year property cost rates DataFrame.

    Output columns:
        city, state, year, effective_tax_rate, insurance_rate,
        total_ancillary_rate, climate_risk_tier,
        tax_source, insurance_source
    """
    rows = []

    for city in CITY_STATE:
        state = CITY_STATE[city]
        climate_tier = CLIMATE_RISK_TIERS[city]
        tax_by_year = TAX_RATES.get(city, {})
        ins_by_year = INSURANCE_RATES.get(city, {})

        missing_years = [y for y in YEARS if y not in tax_by_year or y not in ins_by_year]
        if missing_years:
            print(f"WARNING — {city} missing rates for years: {missing_years}")

        for year in YEARS:
            tax_rate = tax_by_year.get(year)
            ins_rate = ins_by_year.get(year)

            if tax_rate is None or ins_rate is None:
                print(f"SKIP — {city} {year}: missing rate data")
                continue

            rows.append({
                "city": city,
                "state": state,
                "year": year,
                "effective_tax_rate": round(tax_rate, 6),
                "insurance_rate": round(ins_rate, 6),
                "total_ancillary_rate": round(tax_rate + ins_rate, 6),
                "climate_risk_tier": climate_tier,
                "tax_source": "lincoln_institute",
                "insurance_source": "naic_adjusted",
            })

    df = pd.DataFrame(rows)
    return df


def validate_df(df):
    """
    Run basic quality checks before uploading.
    Matches pattern of other loaders — print results, raise on critical failure.
    """
    print("\n--- Validation ---")

    # Row count
    expected_rows = len(CITY_STATE) * len(YEARS)
    actual_rows   = len(df)
    print(f"Expected rows: {expected_rows} | Actual rows: {actual_rows}")
    if actual_rows < expected_rows * 0.95:
        raise ValueError(f"Row count too low: {actual_rows} < {expected_rows * 0.95:.0f}")

    # City coverage
    expected_cities = set(CITY_STATE.keys())
    actual_cities   = set(df["city"].unique())
    missing_cities  = expected_cities - actual_cities
    if missing_cities:
        raise ValueError(f"Missing cities: {missing_cities}")
    print(f"Cities: {df['city'].nunique()} / {len(expected_cities)}")

    # Year coverage
    print(f"Years: {sorted(df['year'].unique())}")

    # Rate sanity checks
    # Tax rates should be between 0.3% and 3.0%
    tax_out_of_range = df[(df["effective_tax_rate"] < 0.003) | (df["effective_tax_rate"] > 0.030)]
    if not tax_out_of_range.empty:
        print(f"WARNING — {len(tax_out_of_range)} rows with unusual tax rates:")
        print(tax_out_of_range[["city", "year", "effective_tax_rate"]])

    # Insurance rates should be between 0.3% and 2.5%
    ins_out_of_range = df[(df["insurance_rate"] < 0.003) | (df["insurance_rate"] > 0.025)]
    if not ins_out_of_range.empty:
        print(f"WARNING — {len(ins_out_of_range)} rows with unusual insurance rates:")
        print(ins_out_of_range[["city", "year", "insurance_rate"]])

    # No nulls in key columns
    for col in ["city", "state", "year", "effective_tax_rate", "insurance_rate"]:
        nulls = df[col].isna().sum()
        if nulls > 0:
            raise ValueError(f"Null values in {col}: {nulls}")

    print(f"Tax rate range: {df['effective_tax_rate'].min():.4f} – {df['effective_tax_rate'].max():.4f}")
    print(f"Insurance rate range:{df['insurance_rate'].min():.4f} – {df['insurance_rate'].max():.4f}")
    print(f"Climate tiers: {df['climate_risk_tier'].value_counts().to_dict()}")
    print("Validation passed")


def upload_table(df, table_name):
    """
    Upload DataFrame to BigQuery — matches pattern of other loaders.
    WRITE_TRUNCATE: full reload on every run (245 rows, negligible cost).
    """
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
    print("Building property cost rates...")
    df = build_property_costs_df()

    print(f"\nTotal rows: {len(df)}")
    print(f"Cities: {df['city'].nunique()}")
    print(f"Years: {sorted(df['year'].unique())}")
    print(f"Date range: {df['year'].min()} → {df['year'].max()}")
    print(df.head(10))

    validate_df(df)

    upload_table(df, "property_cost_rates")
    print("\nLoaded property cost rates")


if __name__ == "__main__":
    main()
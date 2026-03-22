# Housing Market Intelligence Platform
### Macro-Driven Real Estate Analytics & ML Scoring Engine

---

## Overview

A production-grade real estate analytics warehouse that aggregates multi-source housing, macro, and demographic data across **35 U.S. metropolitan markets** into a unified feature pipeline. The platform computes a proprietary **Housing Market Leadership Index (HMLI)** — a 0–100 composite score whose weights are derived via regularized regression on 12-month forward home price appreciation, enabling data-driven market ranking and regime classification.

This is not a dashboard project. It is a **feature engineering and ML scoring system** built on medallion architecture, designed to replicate the kind of quantitative market intelligence used by institutional real estate and PropTech firms.

---

## Architecture

```
Raw Sources (BigQuery)
        │
        ▼
┌─────────────────┐
│   Bronze Layer  │  Ground truth. Type casting, null guards,
│   (Views)       │  deduplication. No business logic.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Silver Layer  │  Metro-filtered, date-standardized feature
│   (Tables)      │  engineering. One model per domain.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Gold Layer    │  City × month flat table. Affordability
│   (Tables)      │  ratios, normalized features, HMLI scores,
└────────┬────────┘  regime labels, city rankings.
         │
         ▼
┌─────────────────┐
│  ML Training    │  Python/scikit-learn. RidgeCV on panel
│  (Python)       │  data. Walk-forward validation. Learned
└────────┬────────┘  HMLI weights.
         │
         ▼
┌─────────────────┐
│  Next.js App    │  Mapbox choropleth, city drill-downs,
│  (Frontend)     │  HMLI trend charts, market regime UI.
└─────────────────┘
```

---

## Data Sources

### Current (Macro & Index Layer)
| Source | Dataset | Grain | Coverage |
|---|---|---|---|
| Zillow | Home Value Index (ZHVI) | Metro × Month | 2018–2025 |
| Zillow | Observed Rent Index (ZORI) | Metro × Month | 2018–2025 |
| FRED | State Macro (unemployment, jobs, permits, wages) | State × Month | 2018–2025 |
| FRED | National Macro (30Y mortgage rate, CPI) | Month | 2018–2025 |
| Census Bureau | Population & Median Income | Metro (static) | Latest ACS |

### Planned (Listing Intelligence Layer)
| Source | Dataset | Grain | Coverage |
|---|---|---|---|
| Scraped (Sale) | Active listings, price cuts, DOM, removals | Listing × Day | Live + historical |
| Scraped (Rental) | Active rentals, vacancy proxy, rent asks | Listing × Day | Live + historical |
| Derived | Absorption rate, inventory change, listing velocity | Metro × Month | Computed from above |
| Derived | Price cut intensity, days-on-market distribution | Metro × Month | Computed from above |

---

## Metro Coverage — 35 U.S. Markets

Markets are segmented into four tiers based on liquidity, data depth, and market archetype:

| Tier | Label | Markets |
|---|---|---|
| 1 | Primary | New York, Los Angeles, San Francisco, Seattle, Chicago, Boston, Washington DC, Miami, Dallas, Houston, San Diego, Minneapolis |
| 2 | Growth | Austin, Phoenix, Atlanta, Nashville, Charlotte, Raleigh, Denver, Tampa, Orlando, Salt Lake City |
| 3 | Secondary | Columbus, Indianapolis, Kansas City, Sacramento, San Jose, Portland, Las Vegas, Jacksonville |
| 4 | Cyclical | Detroit, Pittsburgh, Cleveland, Memphis, Baltimore |

---

## Project Structure
```
properties_analytics/                   # Monorepo root
├── dashboard/                          # Next.js frontend (Mapbox, HMLI UI)
├── docs/                               # Architecture diagrams, methodology notes
├── housing_analytics/                  # dbt project — medallion warehouse
│   ├── models/
│   │   ├── bronze/                     # Raw source staging (views)
│   │   │   ├── bronze_zillow_home_values.sql
│   │   │   ├── bronze_zillow_rent_index.sql
│   │   │   ├── bronze_fred_state_macro.sql
│   │   │   ├── bronze_fred_national_macro.sql
│   │   │   ├── bronze_census_population.sql
│   │   │   ├── sources.yml
│   │   │   └── schema.yml
│   │   ├── silver/                     # Feature engineering (tables)
│   │   │   ├── silver_cities.sql       # Master dimension — all joins through here
│   │   │   ├── silver_home_values.sql  # ZHVI momentum, volatility, HPA target
│   │   │   ├── silver_rent.sql         # ZORI momentum, volatility
│   │   │   ├── silver_macro_national.sql  # Mortgage rate shocks, CPI, regimes
│   │   │   ├── silver_macro_state.sql  # Jobs, unemployment, permits, wages
│   │   │   ├── silver_demographics.sql # Population, income, metro size
│   │   │   └── schema.yml
│   │   └── gold/                       # ML-ready scoring layer (in progress)
│   │       └── schema.yml
│   ├── seeds/
│   │   └── cities.csv                  # 35-city master list with CBSA codes
│   ├── packages.yml
│   └── dbt_project.yml
├── ingestion/                          # Python data loaders → BigQuery
│   ├── detectors/                      # Data quality / anomaly detection
│   └── loaders/                        # Source-specific ingestion scripts
│       ├── load_census_data.py
│       ├── load_fred_national_macro.py
│       ├── load_fred_state_macro.py
│       └── load_zillow_csv.py
├── orchestration/                      # Prefect flows (in progress)
├── scraper/                            # Scrapy listing pipeline
│   ├── spiders/                        # City-level sale + rental spiders
│   ├── utils/                          # Shared scraping utilities
│   ├── items.py                        # Scrapy item schemas
│   ├── middlewares.py                  # Rate limiting, rotation, retries
│   ├── pipelines.py                    # BigQuery write pipeline
│   └── settings.py                     # Scrapy configuration
├── warehouse/                          # Shared BigQuery client utilities
├── .env                                # Credentials (gitignored)
├── pyproject.toml                      # Python project config
├── requirements.txt
└── README.md
```

---

## Medallion Layer Design

### Bronze — Ground Truth
- **Materialized as:** Views (always fresh, zero storage cost)
- **Logic:** Type casting, `SAFE_CAST`, null filtering, column renaming only
- **No filtering** by metro or date — full history preserved
- **Schema:** `housing_bronze`

### Silver — Feature Engineering
- **Materialized as:** Tables
- **Logic:** Filtered to 35 metros via `INNER JOIN` on `silver_cities` seed, date-filtered to `2018-01-01`, all dates standardized via `DATE_TRUNC(date, MONTH)`
- **Pattern:** Every model follows `bronze → joined → base (lags) → features → final SELECT (smoothing/volatility)`
- **Schema:** `housing_silver`

Key silver models:

**`silver_home_values`** — Price momentum engine
- `zhvi_mom_pct`, `zhvi_3m_pct`, `zhvi_yoy_pct` — trailing price signals
- `zhvi_yoy_smooth` — 3-month rolling avg YoY (noise-reduced ML feature)
- `zhvi_volatility_6m` — 6-month rolling stddev (market stability signal)
- `hpa_12m_forward` — **regression target only**, not a feature

**`silver_rent`** — Rent momentum engine
- `zori_mom`, `zori_yoy` — trailing rent signals
- `zori_yoy_smooth`, `zori_mom_3m` — smoothed signals
- `zori_volatility_6m` — rent market stability

**`silver_macro_national`** — Rate & inflation engine
- `mortgage_rate_3m_delta` — short-term rate shock (key HMLI feature)
- `mortgage_rate_12m_delta` — regime-level rate shift
- `mortgage_rate_volatility_6m` — rate uncertainty signal
- `rate_regime`, `inflation_regime` — categorical labels for gold

**`silver_macro_state`** — Labor & supply engine
- `unemployment_3m_delta` — leading labor deterioration signal
- `jobs_3m_pct`, `jobs_yoy_pct` — demand signals (3m smooths BLS revision noise)
- `permits_yoy_pct` — supply pipeline (YoY only — cancels seasonality)
- `wages_yoy_pct` — affordability driver
- `labor_regime`, `supply_regime` — categorical labels for gold

**`silver_demographics`** — Static census dimension
- Joined on `msa_id = cbsa_code` (avoids brittle string matching)
- `monthly_income`, `metro_size` — affordability and normalization inputs

### Gold — Scoring Layer *(in progress)*
- **Materialized as:** Tables
- **Logic:** Single `city × month` flat join of all silver models + affordability ratios + normalized features + HMLI composite score (0–100) + city rank
- **Schema:** `housing_gold`

---

## HMLI Methodology

The Housing Market Leadership Index (HMLI) is a 0–100 composite score built in two phases:

### Phase 1 — Baseline Scoring
Manual weights applied to normalized features. Used to get the dashboard live before ML training data is sufficient.

```
Price momentum:     25%
Rent momentum:      20%
Jobs growth:        15%
Wage growth:        10%
Unemployment:       15%  (inverted — higher = worse)
Affordability:      10%  (inverted — higher = worse)
Mortgage shock:      5%  (inverted)
```

### Phase 2 — Learned Weights (ML)
Weights are derived by fitting a regularized regression (`RidgeCV`) on a panel of city-month observations using `hpa_12m_forward` as the target variable.

**Training setup:**
- Features: standardized with `StandardScaler` (all features on same scale)
- Model: `RidgeCV` with `TimeSeriesSplit` (walk-forward, no data leakage)
- Train: 2018–2022 | Validate: 2023 | Test: 2024
- Output: coefficients → absolute values → normalized to sum to 1 → HMLI weights

**Why regularized regression:**
- Interpretable coefficients map directly to score weights
- Ridge handles correlated macro features (jobs and wages are correlated)
- Stable across city panel without overfitting to specific markets
- Weights are defensible: *"derived from historical predictive power, not manual assignment"*

**Key leakage prevention:**
- `hpa_12m_forward` is computed in silver but **never used as a feature** in gold
- Train/test split is temporal, not random
- All features at month `t` use only data known at `t`

---

## Setup & Running

### Prerequisites
- dbt 1.11+
- BigQuery project with `housing_raw` dataset populated
- GCP OAuth configured

### Installation
```bash
# Clone the repo
git clone https://github.com/AdityaManojMenon/housing-analytics
cd housing_analytics

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dbt and dependencies
pip install dbt-bigquery
dbt deps
```

### Running the Pipeline
```bash
# Seed city master list
dbt seed

# Run full pipeline
dbt run --select bronze
dbt run --select silver
dbt run --select gold         # coming soon

# Run tests
dbt test --select bronze
dbt test --select silver

# Run specific model
dbt run --select silver_home_values --no-partial-parse
```

### Checking Data Quality
```bash
# Preview any model (3 rows)
dbt show --select silver_home_values --limit 3

# Row counts per silver model (run in BigQuery)
SELECT 'home_values' AS model, COUNT(*) AS rows, COUNT(DISTINCT city) AS cities FROM housing_silver.silver_home_values
UNION ALL
SELECT 'rent',        COUNT(*), COUNT(DISTINCT city) FROM housing_silver.silver_rent
UNION ALL
SELECT 'macro_state', COUNT(*), COUNT(DISTINCT state) FROM housing_silver.silver_macro_state
UNION ALL
SELECT 'demographics',COUNT(*), COUNT(DISTINCT city) FROM housing_silver.silver_demographics
```

---

## Key Design Decisions

**Why `DATE_TRUNC(date, MONTH)` everywhere?**
Zillow publishes on month-end dates (2024-01-31), FRED on month-start (2024-01-01). Without truncation, joins between sources produce NULLs. Truncating to month ensures all sources align on the 1st.

**Why `INNER JOIN` to cities seed in silver (not bronze)?**
Bronze preserves ground truth — all metros, all history. Filtering in silver means the city list is a single source of truth (`cities.csv`). Adding or removing a metro requires one seed change, not modifications to 5 bronze models.

**Why YoY for permits and wages, but 3m for jobs?**
Permits and wages are slow-moving or seasonally distorted — MoM is noise. YoY cancels seasonality (permits) and captures structural change (wages). Jobs are a high-frequency leading indicator that the Fed and markets watch monthly — 3m smooths BLS revision noise while preserving the signal.

**Why `RidgeCV` over Lasso or tree models?**
Ridge keeps all features with non-zero coefficients, which matters for a composite score — you want every domain (price, rent, jobs, rates) represented. Lasso can zero out entire feature groups. Trees are not interpretable as score weights.

---

## Roadmap

### Phase 1 — Macro Foundation
- [x] Bronze layer — 5 source models, 15 tests passing
- [x] Silver layer — 6 feature models, 18 tests passing
- [ ] Gold layer — flat join, affordability ratios, baseline HMLI scoring
- [ ] ML training — RidgeCV panel regression, walk-forward validation
- [ ] Phase 1 HMLI — macro-driven composite score, 0–100, city rankings

### Phase 2 — Listing Intelligence Layer
- [ ] Prefect orchestration — scheduled scraping pipeline, retry logic, alerting
- [ ] Sale listing scraper — active listings, price cuts, DOM, removals per city
- [ ] Rental listing scraper — active rentals, rent asks, vacancy proxy per city
- [ ] bronze_listings_sale / bronze_listings_rental — raw scraped tables in BigQuery
- [ ] silver_market_liquidity — derived metro × month metrics:
  - Absorption rate (sales / active inventory)
  - Days on market (median and distribution)
  - Listing velocity (new listings MoM)
  - Price cut intensity (% listings with reductions)
  - Inventory change (active listings YoY)
  - Vacancy rate proxy (rental removals / total listings)

### Phase 3 — Full HMLI
- [ ] Retrain RidgeCV with liquidity features added
- [ ] Compare Phase 1 vs Phase 3 weights — quantify how much liquidity improves R²
- [ ] Phase 3 HMLI — true macro + liquidity composite, validated across 35 metros

### Phase 4 — Frontend
- [ ] Next.js + Mapbox choropleth — HMLI scores by metro
- [ ] City drill-down pages — feature breakdown, regime labels, trend charts
- [ ] HMLI momentum view — 6-month score change, improving vs deteriorating markets
- [ ] Monthly refresh — Prefect triggers dbt run on new data arrival

---

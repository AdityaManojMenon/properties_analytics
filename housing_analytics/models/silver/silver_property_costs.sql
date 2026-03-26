WITH cities AS (
    SELECT DISTINCT city, state
    FROM {{ ref('silver_cities') }}
),

-- Monthly spine — all city × month combinations that exist in home values
-- This is the grain we need to expand annual rates into
monthly_spine AS (
    SELECT DISTINCT
        city,
        month,
        EXTRACT(YEAR FROM month) AS year
    FROM {{ ref('silver_home_values') }}
),

bronze AS (
    SELECT
        city,
        year,
        effective_tax_rate,
        insurance_rate,
        total_ancillary_rate,
        climate_risk_tier,
        tax_source,
        insurance_source
    FROM {{ ref('bronze_property_costs') }}
),

-- Join annual rates to monthly spine on city + year
-- Each month gets the rate for its calendar year
-- If a year is missing (e.g. 2025 not yet published),
-- use LAST_VALUE to forward-fill from most recent available year
joined AS (
    SELECT
        s.city,
        s.month,
        s.year,
        b.effective_tax_rate,
        b.insurance_rate,
        b.total_ancillary_rate,
        b.climate_risk_tier,
        b.tax_source,
        b.insurance_source
    FROM monthly_spine s
    LEFT JOIN bronze b
        ON s.city = b.city
        AND s.year = b.year
),

-- Forward-fill missing years using LAST_VALUE
-- Handles case where current year rates not yet published
forward_filled AS (
    SELECT
        city,
        month,
        year,
        climate_risk_tier,
        tax_source,
        insurance_source,

        -- Forward-fill effective_tax_rate
        LAST_VALUE(effective_tax_rate IGNORE NULLS) OVER (
            PARTITION BY city
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS effective_tax_rate,

        -- Forward-fill insurance_rate
        LAST_VALUE(insurance_rate IGNORE NULLS) OVER (
            PARTITION BY city
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS insurance_rate,

        -- Forward-fill total_ancillary_rate
        LAST_VALUE(total_ancillary_rate IGNORE NULLS) OVER (
            PARTITION BY city
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS total_ancillary_rate

    FROM joined
),

-- Add derived regime labels and monthly cost components
with_regimes AS (
    SELECT
        city,
        month,
        year,
        effective_tax_rate,
        insurance_rate,
        total_ancillary_rate,
        climate_risk_tier,
        tax_source,
        insurance_source,

        -- YoY rate change (now meaningful with time-series data)
        ROUND(
            effective_tax_rate - LAG(effective_tax_rate, 12) OVER (
                PARTITION BY city ORDER BY month
            ), 6
        ) AS tax_rate_yoy_delta,

        ROUND(
            insurance_rate - LAG(insurance_rate, 12) OVER (
                PARTITION BY city ORDER BY month
            ), 6
        ) AS insurance_rate_yoy_delta,

        -- Tax burden regime
        CASE
            WHEN effective_tax_rate >= 0.018 THEN 'high_tax'
            WHEN effective_tax_rate >= 0.010 THEN 'moderate_tax'
            ELSE 'low_tax'
        END AS tax_regime,

        -- Insurance risk regime
        CASE
            WHEN insurance_rate >= 0.010 THEN 'high_risk'
            WHEN insurance_rate >= 0.006 THEN 'moderate_risk'
            ELSE 'standard_risk'
        END AS insurance_risk_tier

    FROM forward_filled
    WHERE effective_tax_rate IS NOT NULL
    AND insurance_rate IS NOT NULL
)

SELECT * FROM with_regimes
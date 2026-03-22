WITH bronze AS (
    SELECT 
        DATE_TRUNC(CAST(date AS DATE), MONTH) AS month,
        series_id,
        value
    FROM {{ ref('bronze_fred_national_macro') }}
    WHERE date >= '2018-01-01'
    AND value IS NOT NULL
),

-- pivot long → wide, one row per cpi and mortgage rate/month
pivoted AS (
    SELECT
        month,
        MAX(CASE WHEN series_id = 'MORTGAGE30US' THEN value END) AS mortgage_rate,
        MAX(CASE WHEN series_id = 'CPIAUCSL' THEN value END) AS cpi
    FROM bronze
    GROUP BY month
),

-- compute all lags once
base AS (
    SELECT
        month,
        mortgage_rate,
        cpi,
        LAG(mortgage_rate, 1)  OVER (ORDER BY month) AS prev_mortgage_1,
        LAG(mortgage_rate, 3) OVER (ORDER BY month) AS prev_mortgage_3,
        LAG(mortgage_rate, 12) OVER (ORDER BY month) AS prev_mortgage_12,
        LAG(cpi, 12) OVER (ORDER BY month) AS prev_cpi_12
    FROM pivoted
    WHERE mortgage_rate IS NOT NULL
    AND cpi IS NOT NULL
),

-- derive features from lags
features AS(
    SELECT
        month,
        mortgage_rate,
        cpi,
        -- MoM mortgage rate change (immediate shock signal)
        ROUND(mortgage_rate - prev_mortgage_1, 4) AS mortgage_rate_mom_delta,
        -- 3-month mortgage rate shock (key HMLI feature)
        ROUND(mortgage_rate - prev_mortgage_3, 4) AS mortgage_rate_3m_delta,
        -- 12-month mortgage rate delta (regime/macro-level shift signal)
        ROUND(mortgage_rate - prev_mortgage_12, 4) AS mortgage_rate_12m_delta,
        -- CPI YoY inflation (real rent growth deflator)
        ROUND(SAFE_DIVIDE(cpi - prev_cpi_12, prev_cpi_12), 4) AS cpi_yoy_pct
    FROM base
)

-- smoothing and volatility require features
SELECT
    month,
    mortgage_rate,
    cpi,
    mortgage_rate_mom_delta,
    mortgage_rate_3m_delta,
    mortgage_rate_12m_delta,
    cpi_yoy_pct,

    -- Smoothed 3m delta (reduces single-month noise)
    ROUND(AVG(mortgage_rate_3m_delta) OVER(ORDER BY month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 4) AS mortgage_rate_3m_smooth,

    -- Rate volatility (6-month rolling stddev — captures rate uncertainty)
    ROUND(STDDEV(mortgage_rate_mom_delta) OVER(ORDER BY month
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW), 4) AS mortgage_rate_volatility_6m,
    
    -- Rate regime label (used in gold for market regime classification)
    CASE
        WHEN mortgage_rate_3m_delta >  0.5  THEN 'rising_fast'
        WHEN mortgage_rate_3m_delta >  0.0  THEN 'rising'
        WHEN mortgage_rate_3m_delta < -0.5  THEN 'falling_fast'
        WHEN mortgage_rate_3m_delta < -0.01  THEN 'falling'
        ELSE 'stable'
    END AS rate_regime,

    -- CPI regime label
    CASE
        WHEN cpi_yoy_pct >= 0.05 THEN 'high_inflation'
        WHEN cpi_yoy_pct >= 0.02 THEN 'moderate_inflation'
        WHEN cpi_yoy_pct >= 0.00 THEN 'low_inflation'
        ELSE 'deflation'
    END AS inflation_regime

FROM features
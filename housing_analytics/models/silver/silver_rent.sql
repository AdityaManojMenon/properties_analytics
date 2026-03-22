WITH cities AS (
    SELECT city, state, tier, zillow_name_lower
    FROM {{ ref('silver_cities') }}
),

bronze AS (
    SELECT
        metro_raw,
        DATE_TRUNC(CAST(date AS DATE), MONTH) AS month,
        rent_index AS zori
    FROM {{ ref('bronze_zillow_rent_index') }}
    WHERE region_type = 'msa'
    AND date >= '2018-01-01'
    AND rent_index IS NOT NULL
),

joined AS (
    SELECT
        c.city,
        c.state,
        c.tier,
        b.month,
        b.zori
    FROM bronze b
    INNER JOIN cities c
        ON b.metro_raw = c.zillow_name_lower
),

base AS (
    SELECT
        city,
        state,
        tier,
        month,
        zori,
        LAG(zori, 1) OVER (PARTITION BY city ORDER BY month) AS prev_zori_1,
        LAG(zori, 3) OVER (PARTITION BY city ORDER BY month) AS prev_zori_3,
        LAG(zori, 12) OVER (PARTITION BY city ORDER BY month) AS prev_zori_12,
        LEAD(zori, 12) OVER (PARTITION BY city ORDER BY month) AS next_zori_12
    FROM joined
), 

-- Compute derived features from base
features AS (
    SELECT
        city,
        state,
        tier,
        month,
        zori,
        -- MoM price change
        ROUND(SAFE_DIVIDE(zori - prev_zori_1, prev_zori_1), 4) AS zori_mom_pct,
        -- 3M Quaterly price change
        ROUND(SAFE_DIVIDE(zori - prev_zori_3, prev_zori_3), 4) AS zori_3m_pct,
        -- YoY price change
        ROUND(SAFE_DIVIDE(zori - prev_zori_12, prev_zori_12), 4) AS zori_yoy_pct,
        -- Regression target 
        ROUND(SAFE_DIVIDE(next_zori_12 - zori, zori), 4) AS hpa_12m_forward
    FROM base
)

-- Feature smoothing CTE using zori_yoy
SELECT
    city,
    state,
    tier,
    month,
    zori,
    zori_mom_pct,
    zori_3m_pct,
    zori_yoy_pct,
    hpa_12m_forward,
    -- Smoothed YoY (3-month rolling avg — reduces noise for ML)
    ROUND(AVG(zori_yoy_pct) OVER(PARTITION BY city ORDER BY month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 4) 
    AS zori_yoy_smooth,

    -- Smoothed MoM (3-month rolling avg — better trend signal than raw MoM)
    ROUND(AVG(zori_mom_pct) OVER(PARTITION BY city ORDER BY month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 4) 
    AS zori_mom_3m,

    -- Volatility (6-month rolling stddev of MoM — risk/stability signal)
    ROUND(STDDEV(zori_mom_pct) OVER(PARTITION BY city ORDER BY month
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW), 4
        ) AS zori_volatility_6m,

FROM features
WHERE zori IS NOT NULL
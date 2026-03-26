WITH cities AS (
    SELECT city, state, tier, zillow_name_lower
    FROM {{ ref('silver_cities') }}
),

bronze AS (
    SELECT
        metro_raw,
        DATE_TRUNC(CAST(date AS DATE), MONTH) AS month,
        home_value_index AS zhvi
    FROM {{ ref('bronze_zillow_home_values') }}
    WHERE region_type = 'msa'
    AND date >= '2018-01-01'
    AND home_value_index IS NOT NULL
),

joined AS (
    SELECT
        c.city,
        c.state,
        c.tier,
        b.month,
        b.zhvi
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
        zhvi,
        LAG(zhvi, 1) OVER (PARTITION BY city ORDER BY month) AS prev_zhvi_1,
        LAG(zhvi, 3) OVER (PARTITION BY city ORDER BY month) AS prev_zhvi_3,
        LAG(zhvi, 12) OVER (PARTITION BY city ORDER BY month) AS prev_zhvi_12,
        LEAD(zhvi, 12) OVER (PARTITION BY city ORDER BY month) AS next_zhvi_12
    FROM joined
), 

-- Compute derived features from base
features AS (
    SELECT
        city,
        state,
        tier,
        month,
        zhvi,
        -- MoM price change
        ROUND(SAFE_DIVIDE(zhvi - prev_zhvi_1, prev_zhvi_1), 4) AS zhvi_mom_pct,
        -- Quater/3M growth
        ROUND(SAFE_DIVIDE(zhvi - prev_zhvi_3,  prev_zhvi_3),  4) AS zhvi_3m_pct,
        -- YoY price change
        ROUND(SAFE_DIVIDE(zhvi - prev_zhvi_12, prev_zhvi_12), 4) AS zhvi_yoy_pct,
        -- Regression target 
        ROUND(SAFE_DIVIDE(next_zhvi_12 - zhvi, zhvi), 4) AS hpa_12m_forward
    FROM base
),

national_hpa AS (
    SELECT
        month,
        AVG(hpa_12m_forward) AS national_hpa
    FROM features
    WHERE hpa_12m_forward IS NOT NULL
    GROUP BY month
)

SELECT
    f.city,
    f.state,
    f.tier,
    f.month,
    f.zhvi,
    f.zhvi_mom_pct,
    f.zhvi_3m_pct,
    f.zhvi_yoy_pct,
    f.hpa_12m_forward,
    n.national_hpa,
    ROUND(f.hpa_12m_forward - n.national_hpa, 6) AS hpa_relative,

    ROUND(
        AVG(f.zhvi_yoy_pct) OVER (
            PARTITION BY f.city ORDER BY f.month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 4
    ) AS zhvi_yoy_smooth,

    ROUND(
        AVG(f.zhvi_mom_pct) OVER (
            PARTITION BY f.city ORDER BY f.month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 4
    ) AS zhvi_mom_3m,

    ROUND(
        STDDEV(f.zhvi_mom_pct) OVER (
            PARTITION BY f.city ORDER BY f.month
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ), 4
    ) AS zhvi_volatility_6m

FROM features f
LEFT JOIN national_hpa n
    ON f.month = n.month
WHERE f.zhvi IS NOT NULL
WITH city_states AS (
    -- Only pull states that appear in your 35-city list
    SELECT DISTINCT state
    FROM {{ ref('silver_cities') }}
),

bronze AS (
    SELECT
        state,
        DATE_TRUNC(CAST(date AS DATE), MONTH)   AS month,
        metric,
        value
    FROM {{ ref('bronze_fred_state_macro') }}
    WHERE date >= '2018-01-01'
    AND value IS NOT NULL
),

--  Filter to only states in your 35-city list
filtered AS (
    SELECT b.*
    FROM bronze b
    INNER JOIN city_states c ON b.state = c.state
),

-- pivot long → wide, one row per state/month
pivoted AS (
    SELECT
        state,
        month,
        MAX(CASE WHEN metric = 'unemployment' THEN value END) AS unemployment_rate,
        MAX(CASE WHEN metric = 'nonfarm_jobs'  THEN value END) AS nonfarm_jobs,
        MAX(CASE WHEN metric = 'permits'       THEN value END) AS building_permits,
        MAX(CASE WHEN metric = 'hourly_wages'  THEN value END) AS hourly_wages
    FROM filtered
    GROUP BY state, month
),

-- compute all lags once
base AS (
    SELECT
        state,
        month,
        unemployment_rate,
        nonfarm_jobs,
        building_permits,
        hourly_wages,

        -- Unemployment lags
        LAG(unemployment_rate, 1) OVER (PARTITION BY state ORDER BY month) AS prev_unemp_1,
        LAG(unemployment_rate, 3) OVER (PARTITION BY state ORDER BY month) AS prev_unemp_3,
        LAG(unemployment_rate, 12) OVER (PARTITION BY state ORDER BY month) AS prev_unemp_12,

        -- Jobs lags
        LAG(nonfarm_jobs, 1) OVER (PARTITION BY state ORDER BY month) AS prev_jobs_1,
        LAG(nonfarm_jobs, 3)  OVER (PARTITION BY state ORDER BY month) AS prev_jobs_3,
        LAG(nonfarm_jobs, 12) OVER (PARTITION BY state ORDER BY month) AS prev_jobs_12,

        -- Permits lags
        LAG(building_permits, 12) OVER (PARTITION BY state ORDER BY month) AS prev_permits_12,
        
        -- Wages lags
        LAG(hourly_wages, 12) OVER (PARTITION BY state ORDER BY month) AS prev_wages_12
    FROM pivoted
),

-- derive features from lags
features AS (
    SELECT
        state,
        month,
        unemployment_rate,
        nonfarm_jobs,
        building_permits,
        hourly_wages,
        -- Unemployment deltas (rising = bearish demand signal)
        ROUND(unemployment_rate - prev_unemp_1,  4) AS unemployment_mom_delta,
        ROUND(unemployment_rate - prev_unemp_3,  4) AS unemployment_3m_delta,
        ROUND(unemployment_rate - prev_unemp_12, 4) AS unemployment_yoy_delta,
        -- Jobs pct change 3m 
        ROUND(SAFE_DIVIDE(nonfarm_jobs - prev_jobs_1,prev_jobs_1), 4) AS jobs_mom_pct,
        ROUND(SAFE_DIVIDE(nonfarm_jobs - prev_jobs_3,prev_jobs_3), 4) AS jobs_3m_pct
        ROUND(SAFE_DIVIDE(nonfarm_jobs - prev_jobs_12,prev_jobs_12), 4) AS jobs_yoy_pct,
        -- Permits YoY (only YoY because it mitegates short term seasonal volitility)
        ROUND(SAFE_DIVIDE(building_permits - prev_permits_12,prev_permits_12), 4) AS permits_yoy_pct,
        -- Wages YoY (affordability driver)
        ROUND(SAFE_DIVIDE(hourly_wages - prev_wages_12,prev_wages_12), 4) AS wages_yoy_pct
    FROM base
)

-- smoothing and volatility require features
SELECT
    state,
    month,
    unemployment_rate,
    nonfarm_jobs,
    building_permits,
    hourly_wages,
    unemployment_mom_delta,
    unemployment_3m_delta,
    unemployment_yoy_delta,
    job_mom_pct,
    jobs_yoy_pct,
    jobs_3m_pct,
    permits_yoy_pct,
    wages_yoy_pct, 

    -- Smoothed unemployment trend (3m rolling avg to reduce noise)
    ROUND(AVG(unemployment_3m_delta) OVER(PARTITION BY state
        ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 4
    ) AS unemployment_3m_smooth,

    -- Jobs momentum smoothed (3m rolling avg)
    ROUND(AVG(jobs_3m_pct) OVER(PARTITION BY state 
        ORDER BY month ROW BETWEEN 2 PRECEDING AND CURRENT), 4
    ) AS jobs_3m_smooth,

    -- Jobs volatility (stddev of 3m pct
    ROUND(STDDEV(jobs_3m_pct) OVER(PARTITION BY state 
        ORDER BY month ROW BETWEEN 2 PRECEDING AND CURRENT), 4
    ) AS jobs_volatility_6m,

    -- Permits volatility (6m rolling stddev — supply pipeline uncertainty)
    ROUND(STDDEV(permits_yoy_pct) OVER (PARTITION BY state
        ORDER BY month ROWS BETWEEN 5 PRECEDING AND CURRENT ROW), 4
    ) AS permits_volatility_6m,

    -- Labor market regime label (used in gold for market regime classification)
    CASE
        WHEN unemployment_3m_delta >  0.5 THEN 'deteriorating_fast'
        WHEN unemployment_3m_delta >  0.0 THEN 'deteriorating'
        WHEN unemployment_3m_delta < -0.5 THEN 'improving_fast'
        WHEN unemployment_3m_delta < -0.0 THEN 'improving'
        ELSE 'stable'
    END AS labor_regime,

    -- Supply regime label (used in gold for supply constraint scoring)
    CASE
        WHEN permits_yoy_pct >  0.15 THEN 'supply_expanding'
        WHEN permits_yoy_pct >  0.00 THEN 'supply_growing'
        WHEN permits_yoy_pct < -0.15 THEN 'supply_contracting_fast'
        WHEN permits_yoy_pct < -0.00 THEN 'supply_contracting'
        ELSE 'supply_stable'
    END AS supply_regime

FROM features




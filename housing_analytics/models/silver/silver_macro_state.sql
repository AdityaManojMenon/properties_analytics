WITH city_states AS (
    SELECT DISTINCT state
    FROM {{ ref('silver_cities') }}
),

-- Month spine from your city-month core table
month_spine AS (
    SELECT DISTINCT month
    FROM {{ ref('silver_home_values') }}
),

state_month_spine AS (
    SELECT
        s.state,
        m.month
    FROM city_states s
    CROSS JOIN month_spine m
),

bronze AS (
    SELECT
        state,
        DATE_TRUNC(CAST(date AS DATE), MONTH) AS month,
        metric,
        value
    FROM {{ ref('bronze_fred_state_macro') }}
    WHERE date >= '2018-01-01'
      AND value IS NOT NULL
),

filtered AS (
    SELECT b.*
    FROM bronze b
    INNER JOIN city_states c
        ON b.state = c.state
),

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

-- Join the real observations onto a full state x month spine
spined AS (
    SELECT
        s.state,
        s.month,
        p.unemployment_rate,
        p.nonfarm_jobs,
        p.building_permits,
        p.hourly_wages
    FROM state_month_spine s
    LEFT JOIN pivoted p
        ON s.state = p.state
       AND s.month = p.month
),

-- Forward-fill each metric independently by state
filled AS (
    SELECT
        state,
        month,

        LAST_VALUE(unemployment_rate IGNORE NULLS) OVER (
            PARTITION BY state
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS unemployment_rate,

        LAST_VALUE(nonfarm_jobs IGNORE NULLS) OVER (
            PARTITION BY state
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS nonfarm_jobs,

        LAST_VALUE(building_permits IGNORE NULLS) OVER (
            PARTITION BY state
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS building_permits,

        LAST_VALUE(hourly_wages IGNORE NULLS) OVER (
            PARTITION BY state
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS hourly_wages
    FROM spined
),

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
        LAG(nonfarm_jobs, 1)  OVER (PARTITION BY state ORDER BY month) AS prev_jobs_1,
        LAG(nonfarm_jobs, 3)  OVER (PARTITION BY state ORDER BY month) AS prev_jobs_3,
        LAG(nonfarm_jobs, 12) OVER (PARTITION BY state ORDER BY month) AS prev_jobs_12,

        -- Permits lags
        LAG(building_permits, 12) OVER (PARTITION BY state ORDER BY month) AS prev_permits_12,

        -- Wages lags
        LAG(hourly_wages, 12) OVER (PARTITION BY state ORDER BY month) AS prev_wages_12
    FROM filled
),

features AS (
    SELECT
        state,
        month,
        unemployment_rate,
        nonfarm_jobs,
        building_permits,
        hourly_wages,

        ROUND(unemployment_rate - prev_unemp_1, 4) AS unemployment_mom_delta,
        ROUND(unemployment_rate - prev_unemp_3, 4) AS unemployment_3m_delta,
        ROUND(unemployment_rate - prev_unemp_12, 4) AS unemployment_yoy_delta,

        ROUND(SAFE_DIVIDE(nonfarm_jobs - prev_jobs_1,  prev_jobs_1), 4) AS jobs_mom_pct,
        ROUND(SAFE_DIVIDE(nonfarm_jobs - prev_jobs_3,  prev_jobs_3), 4) AS jobs_3m_pct,
        ROUND(SAFE_DIVIDE(nonfarm_jobs - prev_jobs_12, prev_jobs_12), 4) AS jobs_yoy_pct,

        ROUND(SAFE_DIVIDE(building_permits - prev_permits_12, prev_permits_12), 4) AS permits_yoy_pct,
        ROUND(SAFE_DIVIDE(hourly_wages - prev_wages_12, prev_wages_12), 4) AS wages_yoy_pct
    FROM base
)

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
    jobs_mom_pct,
    jobs_yoy_pct,
    jobs_3m_pct,
    permits_yoy_pct,
    wages_yoy_pct,

    ROUND(
        AVG(unemployment_3m_delta) OVER (
            PARTITION BY state
            ORDER BY month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 4
    ) AS unemployment_3m_smooth,

    ROUND(
        AVG(jobs_3m_pct) OVER (
            PARTITION BY state
            ORDER BY month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 4
    ) AS jobs_3m_smooth,

    ROUND(
        STDDEV(jobs_3m_pct) OVER (
            PARTITION BY state
            ORDER BY month
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ), 4
    ) AS jobs_volatility_6m,

    ROUND(
        STDDEV(permits_yoy_pct) OVER (
            PARTITION BY state
            ORDER BY month
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ), 4
    ) AS permits_volatility_6m,

    CASE
        WHEN unemployment_3m_delta >  0.5 THEN 'deteriorating_fast'
        WHEN unemployment_3m_delta >  0.0 THEN 'deteriorating'
        WHEN unemployment_3m_delta < -0.5 THEN 'improving_fast'
        WHEN unemployment_3m_delta <  0.0 THEN 'improving'
        ELSE 'stable'
    END AS labor_regime,

    CASE
        WHEN permits_yoy_pct >  0.15 THEN 'supply_expanding'
        WHEN permits_yoy_pct >  0.00 THEN 'supply_growing'
        WHEN permits_yoy_pct < -0.15 THEN 'supply_contracting_fast'
        WHEN permits_yoy_pct <  0.00 THEN 'supply_contracting'
        ELSE 'supply_stable'
    END AS supply_regime

FROM features
WHERE month >= '2018-01-01'
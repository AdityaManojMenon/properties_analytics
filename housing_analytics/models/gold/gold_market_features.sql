-- Flat joins of all silver layer tables and affordability ratios

WITH cities AS (
    SELECT
        city,
        state,
        tier,
        tier_label,
        lat,
        lng,
        cbsa_code
    FROM {{ ref('silver_cities') }}
),

home_values AS (
    SELECT
        city,
        month,
        zhvi,
        zhvi_mom_pct,
        zhvi_3m_pct,
        zhvi_yoy_pct,
        zhvi_yoy_smooth,
        zhvi_mom_3m,
        zhvi_volatility_6m,
        hpa_12m_forward 
    FROM {{ ref('silver_home_values') }}
),

rent AS (
    SELECT
        city,
        month,
        zori,
        zori_mom_pct,
        zori_3m_pct,
        zori_yoy_pct,
        zori_yoy_smooth,
        zori_mom_3m,   
        zori_volatility_6m
    FROM {{ ref('silver_rent') }}
),

macro_national AS (
    SELECT 
        month,
        mortgage_rate,
        cpi,
        mortgage_rate_mom_delta,
        mortgage_rate_3m_delta,
        mortgage_rate_12m_delta,
        mortgage_rate_3m_smooth,
        mortgage_rate_volatility_6m,
        cpi_yoy_pct,
        rate_regime,
        inflation_regime
    FROM {{ ref('silver_macro_national') }}
),    

macro_state AS (
    SELECT
        state,
        month,
        unemployment_rate,
        unemployment_mom_delta,
        unemployment_3m_delta,
        unemployment_yoy_delta,
        unemployment_3m_smooth,
        jobs_3m_pct,
        jobs_yoy_pct,
        jobs_3m_smooth,
        jobs_volatility_6m,
        permits_yoy_pct,
        permits_volatility_6m,
        wages_yoy_pct,
        labor_regime,
        supply_regime
    FROM {{ ref('silver_macro_state') }}
),

demographics AS (
    SELECT
        city,
        population,
        median_income,
        monthly_income,
        metro_size
    FROM {{ ref('silver_demographics') }}
),

-- Core join: city × month spine from home_values 
-- Everything joins to this

joined AS (
    SELECT
        -- home value columns enabling joins
        hv.city,
        hv.month,

        -- cities columns enabling joins
        c.state,
        c.tier,
        c.tier_label,
        c.lat,
        c.lng,

        -- home value features
        hv.zhvi,
        hv.zhvi_mom_pct,
        hv.zhvi_3m_pct,
        hv.zhvi_yoy_pct,
        hv.zhvi_yoy_smooth,
        hv.zhvi_mom_3m,
        hv.zhvi_volatility_6m,
        hv.hpa_12m_forward,

        -- rent features
        r.zori,
        r.zori_mom_pct,
        r.zori_yoy_pct,
        r.zori_yoy_smooth,
        zori_mom_3m,
        r.zori_volatility_6m,

        -- national macro (same for all cities in same month)
        n.mortgage_rate,
        n.cpi,
        n.mortgage_rate_mom_delta,
        n.mortgage_rate_3m_delta,
        n.mortgage_rate_12m_delta,
        n.mortgage_rate_3m_smooth,
        n.mortgage_rate_volatility_6m,
        n.cpi_yoy_pct,
        n.rate_regime,
        n.inflation_regime,

        -- State macro (shared within state)
        s.unemployment_rate,
        s.unemployment_mom_delta,
        s.unemployment_3m_delta,
        s.unemployment_yoy_delta,
        s.unemployment_3m_smooth,
        s.jobs_3m_pct,
        s.jobs_yoy_pct,
        s.jobs_3m_smooth,
        s.jobs_volatility_6m,
        s.permits_yoy_pct,
        s.permits_volatility_6m,
        s.wages_yoy_pct,
        s.labor_regime,
        s.supply_regime,

        -- Demographics (static, same every month per city)
        d.population,
        d.median_income,
        d.monthly_income,
        d.metro_size

        FROM home_values hv
        INNER JOIN cities c 
        ON hv.city = c.city 
        LEFT JOIN rent r 
        ON hv.city = r.city AND hv.month = r.month
        LEFT JOIN macro_national n
        ON hv.month = n.month 
        LEFT JOIN macro_state s 
        ON c.state = s.state AND hv.month = s.month
        LEFT JOIN demographics d 
        ON hv.city = d.city
),

-- Affordability ratios using zhvi + zori + income

affordability_ratios AS (
    SELECT
        *,
        -- Price-to-income ratio (how many years of income to buy)
        ROUND(SAFE_DIVIDE(zhvi, median_income), 2) AS price_to_income_ratio,

        -- Monthly mortgage payment estimate (30Y fixed, 20% down)
        -- Payment = P * [r(1+r)^n] / [(1+r)^n - 1] (P: Principal, r: mortgage rate, n number of payments -> 12 per year * 30 year)
        ROUND(SAFE_DIVIDE(
            (zhvi * 0.8) * (mortgage_rate/1200) * POWER(1 + (mortgage_rate/1200), 360),
            POWER(1 + (mortgage_rate/1200), 360) - 1), 2) AS monthly_mortgage_payment,

        -- Mortgage-to-income ratio (monthly payment as % of monthly income)
        -- Above 0.30 = cost-burdened threshold
        ROUND(
            SAFE_DIVIDE(
                (zhvi * 0.8) *
                SAFE_DIVIDE(
                    (mortgage_rate / 1200) *
                    POWER(1 + (mortgage_rate / 1200), 360),
                    POWER(1 + (mortgage_rate / 1200), 360) - 1
                ),  monthly_income
                ), 4 
            ) AS mortgage_to_income_ratio,

        -- Rent-to-income ratio (monthly rent as % of monthly income)
        -- Above 0.30 = rent-burdened threshold
        ROUND(SAFE_DIVIDE(zori, monthly_income), 4) AS rent_to_income_ratio,

        -- Price-to-rent ratio (buy vs rent signal)
        -- Above 20 = renting cheaper, below 15 = buying cheaper
        ROUND(SAFE_DIVIDE(zhvi, zori * 12), 2)
            AS price_to_rent_ratio

    FROM joined
)

SELECT * FROM affordability_ratios

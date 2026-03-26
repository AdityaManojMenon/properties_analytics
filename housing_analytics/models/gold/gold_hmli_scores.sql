WITH base AS (
    SELECT
        city,
        state,
        tier,
        month,

        -- Housing momentum
        zhvi_yoy_smooth,
        zhvi_mom_3m,
        zhvi_volatility_6m,

        -- Rent strength
        zori_yoy_smooth,
        zori_mom_3m,
        zori_volatility_6m,

        -- Labor
        unemployment_rate,
        unemployment_3m_delta,
        jobs_yoy_pct,

        -- Supply
        permits_yoy_pct,

        -- Macro / rates
        mortgage_rate_3m_delta,
        mortgage_rate_volatility_6m,
        cpi_yoy_pct,

        -- Affordability
        price_to_income_ratio,
        piti_rate_pressure,
        rent_to_income_ratio,
        piti_shock

    FROM {{ ref('gold_market_features') }}
),

ranked AS (
    SELECT
        *,

        -- =========================
        -- Housing momentum
        -- higher growth = better
        -- higher volatility = worse
        -- =========================
        PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY zhvi_yoy_smooth
        ) AS zhvi_yoy_smooth_score,

        PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY zhvi_mom_3m
        ) AS zhvi_mom_3m_score,

        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY zhvi_volatility_6m
        ) AS zhvi_volatility_6m_score,

        -- =========================
        -- Rent strength
        -- higher growth = better
        -- higher volatility = worse
        -- =========================
        PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY zori_yoy_smooth
        ) AS zori_yoy_smooth_score,

        PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY zori_mom_3m
        ) AS zori_mom_3m_score,

        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY zori_volatility_6m
        ) AS zori_volatility_6m_score,

        -- =========================
        -- Labor
        -- lower unemployment = better
        -- lower unemployment delta = better
        -- higher jobs growth = better
        -- =========================
        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY unemployment_rate
        ) AS unemployment_rate_score,

        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY unemployment_3m_delta
        ) AS unemployment_3m_delta_score,

        PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY jobs_yoy_pct
        ) AS jobs_yoy_pct_score,

        -- =========================
        -- Labor supply
        -- here higher permits = better from a growth/market-health lens
        -- if you want constrained supply to be rewarded instead,
        -- flip this direction later
        -- =========================
        PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY permits_yoy_pct
        ) AS permits_yoy_pct_score,

        -- =========================
        -- Macro / rates
        -- higher inflation/rate shock/vol = worse
        -- =========================
        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY mortgage_rate_3m_delta
        ) AS mortgage_rate_3m_delta_score,

        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY mortgage_rate_volatility_6m
        ) AS mortgage_rate_volatility_6m_score,

        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY cpi_yoy_pct
        ) AS cpi_yoy_pct_score,

        -- =========================
        -- Affordability
        -- higher burden/stretch/shock = worse
        -- =========================
        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY price_to_income_ratio
        ) AS price_to_income_ratio_score,

        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY piti_rate_pressure
        ) AS piti_rate_pressure_score,

        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY rent_to_income_ratio
        ) AS rent_to_income_ratio_score,

        1 - PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY piti_shock
        ) AS piti_shock_score

    FROM base
),

bucketed AS (
    SELECT
        *,

        -- Bucket scores
        ROUND((
            zhvi_yoy_smooth_score +
            zhvi_mom_3m_score +
            zhvi_volatility_6m_score
        ) / 3, 6) AS housing_momentum_score,

        ROUND((
            zori_yoy_smooth_score +
            zori_mom_3m_score +
            zori_volatility_6m_score
        ) / 3, 6) AS rent_strength_score,

        ROUND((
            unemployment_rate_score +
            unemployment_3m_delta_score +
            jobs_yoy_pct_score
        ) / 3, 6) AS labor_score,

        ROUND(permits_yoy_pct_score, 6) AS labor_supply_score,

        ROUND((
            mortgage_rate_3m_delta_score +
            mortgage_rate_volatility_6m_score +
            cpi_yoy_pct_score
        ) / 3, 6) AS macro_rates_score,

        ROUND((
            price_to_income_ratio_score +
            piti_rate_pressure_score +
            rent_to_income_ratio_score +
            piti_shock_score
        ) / 4, 6) AS affordability_score

    FROM ranked
),

final AS (
    SELECT
        city,
        state,
        tier,
        month,

        -- Raw inputs
        zhvi_yoy_smooth,
        zhvi_mom_3m,
        zhvi_volatility_6m,
        zori_yoy_smooth,
        zori_mom_3m,
        zori_volatility_6m,
        unemployment_rate,
        unemployment_3m_delta,
        jobs_yoy_pct,
        permits_yoy_pct,
        mortgage_rate_3m_delta,
        mortgage_rate_volatility_6m,
        cpi_yoy_pct,
        price_to_income_ratio,
        piti_rate_pressure,
        rent_to_income_ratio,
        piti_shock,

        -- Feature scores
        zhvi_yoy_smooth_score,
        zhvi_mom_3m_score,
        zhvi_volatility_6m_score,
        zori_yoy_smooth_score,
        zori_mom_3m_score,
        zori_volatility_6m_score,
        unemployment_rate_score,
        unemployment_3m_delta_score,
        jobs_yoy_pct_score,
        permits_yoy_pct_score,
        mortgage_rate_3m_delta_score,
        mortgage_rate_volatility_6m_score,
        cpi_yoy_pct_score,
        price_to_income_ratio_score,
        piti_rate_pressure_score,
        rent_to_income_ratio_score,
        piti_shock_score,

        -- Bucket scores
        housing_momentum_score,
        rent_strength_score,
        labor_score,
        labor_supply_score,
        macro_rates_score,
        affordability_score,

        -- Final HMLI score from ML model
        ROUND(
            0.42 * rent_strength_score
            + 0.34 * housing_momentum_score
            + 0.15 * affordability_score
            + 0.08 * labor_score
            + 0.01 * labor_supply_score
        , 6) AS hmli_score

    FROM bucketed
)

SELECT * FROM final
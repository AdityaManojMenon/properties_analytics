WITH base AS (
    SELECT
        city,
        state,
        tier,
        tier_label,
        month,
        lat,
        lng,

        -- Raw housing / rent levels
        zhvi,
        zori,

        -- Housing momentum inputs
        zhvi_yoy_smooth,
        zhvi_mom_3m,
        zhvi_volatility_6m,

        -- Rent strength inputs
        zori_yoy_smooth,
        zori_mom_3m,
        zori_volatility_6m,

        -- Labor / supply inputs
        unemployment_rate,
        unemployment_mom_delta,
        unemployment_3m_delta,
        unemployment_yoy_delta,
        unemployment_3m_smooth,
        jobs_yoy_pct,
        jobs_3m_smooth,
        jobs_volatility_6m,
        permits_yoy_pct,
        permits_volatility_6m,
        wages_yoy_pct,

        -- Macro inputs
        mortgage_rate,
        mortgage_rate_mom_delta,
        mortgage_rate_3m_delta,
        mortgage_rate_12m_delta,
        mortgage_rate_3m_smooth,
        mortgage_rate_volatility_6m,
        cpi,
        cpi_yoy_pct,

        -- Affordability / payment inputs
        price_to_income_ratio,
        mortgage_to_income_ratio,
        piti_to_income_ratio,
        rent_to_income_ratio,
        price_to_rent_ratio,
        monthly_mortgage_payment,
        monthly_property_tax,
        monthly_insurance,
        monthly_piti,
        piti_rate_pressure,
        piti_shock,
        affordability_class,

        -- Regimes
        labor_regime,
        supply_regime,
        rate_regime,
        inflation_regime,
        tax_regime,
        insurance_risk_tier,

        -- Demographics
        population,
        median_income,
        monthly_income,
        metro_size,

        -- Targets / diagnostics
        hpa_12m_forward,
        national_hpa,
        hpa_relative

    FROM {{ ref('gold_market_features') }}
),

ranked AS (
    SELECT
        *,

        -- =========================
        -- Housing momentum
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
        -- higher permits = stronger supply / growth support
        -- =========================
        PERCENT_RANK() OVER (
            PARTITION BY month ORDER BY permits_yoy_pct
        ) AS permits_yoy_pct_score,

        -- =========================
        -- Macro / rates
        -- national variables -> contextual only
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
        *,

        -- Updated structural weights
        ROUND(
              0.423767 * rent_strength_score
            + 0.338197 * housing_momentum_score
            + 0.147739 * affordability_score
            + 0.079770 * labor_score
            + 0.010528 * labor_supply_score
        , 6) AS hmli_score

    FROM bucketed
)

SELECT * FROM final
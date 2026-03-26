WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY city
            ORDER BY month DESC
        ) AS rn
    FROM {{ ref('gold_hmli_scores') }}
),

latest AS (
    SELECT
        city,
        state,
        tier,
        tier_label,
        month,
        lat,
        lng,

        -- Final score + rank inputs
        hmli_score,
        housing_momentum_score,
        rent_strength_score,
        affordability_score,
        labor_score,
        labor_supply_score,
        macro_rates_score,

        -- Housing / rent raw levels
        zhvi,
        zori,

        -- Housing signals
        zhvi_yoy_smooth,
        zhvi_mom_3m,
        zhvi_volatility_6m,

        -- Rent signals
        zori_yoy_smooth,
        zori_mom_3m,
        zori_volatility_6m,

        -- Score components
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

        -- Affordability / investment economics
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

        -- State labor / supply metrics
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

        -- National macro metrics
        mortgage_rate,
        mortgage_rate_mom_delta,
        mortgage_rate_3m_delta,
        mortgage_rate_12m_delta,
        mortgage_rate_3m_smooth,
        mortgage_rate_volatility_6m,
        cpi,
        cpi_yoy_pct,

        -- Regime labels
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

    FROM ranked
    WHERE rn = 1
),

final AS (
    SELECT
        *,
        RANK() OVER (ORDER BY hmli_score DESC) AS hmli_rank,
        NTILE(5) OVER (ORDER BY hmli_score DESC) AS hmli_quintile,
        NTILE(10) OVER (ORDER BY hmli_score DESC) AS hmli_decile
    FROM latest
)

SELECT *
FROM final
ORDER BY hmli_score DESC
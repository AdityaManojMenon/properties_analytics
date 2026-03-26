SELECT
    LOWER(TRIM(city))               AS city,
    UPPER(TRIM(state))              AS state,
    CAST(year AS INT64)             AS year,
    SAFE_CAST(effective_tax_rate AS FLOAT64)    AS effective_tax_rate,
    SAFE_CAST(insurance_rate AS FLOAT64)        AS insurance_rate,
    SAFE_CAST(total_ancillary_rate AS FLOAT64)  AS total_ancillary_rate,
    LOWER(TRIM(climate_risk_tier))  AS climate_risk_tier,
    LOWER(TRIM(tax_source))         AS tax_source,
    LOWER(TRIM(insurance_source))   AS insurance_source
FROM {{ source('housing_raw', 'property_cost_rates') }}
WHERE effective_tax_rate IS NOT NULL
AND insurance_rate IS NOT NULL
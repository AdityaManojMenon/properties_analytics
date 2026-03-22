SELECT
    CAST(date AS DATE)              AS date,
    SAFE_CAST(value AS FLOAT64)     AS value,
    UPPER(TRIM(state))              AS state,
    LOWER(TRIM(metric))             AS metric,
    UPPER(TRIM(series_id))          AS series_id,
    LOWER(TRIM(source))             AS source,
    LOWER(TRIM(frequency))          AS frequency,
    CAST(seasonally_adjusted AS BOOL) AS seasonally_adjusted
FROM {{ source('housing_raw', 'fred_state_macro') }}
WHERE value IS NOT NULL
AND date IS NOT NULL
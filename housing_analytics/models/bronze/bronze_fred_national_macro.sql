SELECT
    CAST(date AS DATE)              AS date,
    SAFE_CAST(value AS FLOAT64)     AS value,
    UPPER(TRIM(series_id))          AS series_id,
    LOWER(TRIM(source))             AS source
FROM {{ source('housing_raw', 'fred_national_macro') }}
WHERE value IS NOT NULL
AND CAST(date AS DATE) <= CURRENT_DATE()
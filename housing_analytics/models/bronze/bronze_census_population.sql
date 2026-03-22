SELECT
    LOWER(TRIM(metro))              AS metro_raw,
    SAFE_CAST(population AS INT64)  AS population,
    SAFE_CAST(median_income AS INT64) AS median_income,
    SAFE_CAST(msa_id AS INT64)      AS msa_id,
    LOWER(TRIM(source))             AS source
FROM {{ source('housing_raw', 'census_population') }}
WHERE population IS NOT NULL
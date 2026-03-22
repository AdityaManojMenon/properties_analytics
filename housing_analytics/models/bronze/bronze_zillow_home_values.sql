SELECT
    CAST(RegionID AS INT64)         AS region_id,
    CAST(SizeRank AS INT64)         AS size_rank,
    LOWER(TRIM(metro))              AS metro_raw,
    LOWER(TRIM(RegionType))         AS region_type,
    UPPER(TRIM(state))              AS state,
    CAST(date AS DATE)              AS date,
    SAFE_CAST(home_value_index AS FLOAT64) AS home_value_index,
    LOWER(TRIM(source))             AS source
FROM {{ source('housing_raw', 'zillow_home_values') }}
WHERE home_value_index IS NOT NULL
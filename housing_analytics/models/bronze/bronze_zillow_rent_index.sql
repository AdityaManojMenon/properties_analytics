SELECT
    CAST(RegionID AS INT64)         AS region_id,
    CAST(SizeRank AS INT64)         AS size_rank,
    LOWER(TRIM(metro))              AS metro_raw,
    LOWER(TRIM(RegionType))         AS region_type,
    UPPER(TRIM(state))              AS state,
    CAST(date AS DATE)              AS date,
    SAFE_CAST(rent_index AS FLOAT64) AS rent_index,
    LOWER(TRIM(source))             AS source
FROM {{ source('housing_raw', 'zillow_rent_index') }}
WHERE rent_index IS NOT NULL
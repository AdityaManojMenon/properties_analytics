SELECT
    city_slug AS city,
    display_name,
    state,
    tier,
    lat,
    lng,
    LOWER(zillow_name) AS zillow_name_lower,
    cbsa_code,
    CASE tier
        WHEN 1 THEN 'Primary Market'
        WHEN 2 THEN 'Growth Market'
        WHEN 3 THEN 'Emerging Market'
    END AS tier_label
FROM {{ ref('cities') }}
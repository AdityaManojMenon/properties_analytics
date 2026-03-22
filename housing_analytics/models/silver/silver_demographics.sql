WITH bronze AS(
    SELECT
        msa_id,
        population,
        median_income
    FROM {{ ref('bronze_census_population') }}
    WHERE population IS NOT NULL
),

cities AS(
    SELECT
        city,
        state,
        tier,
        cbsa_code
    FROM {{ ref('silver_cities') }}
),

joined AS(
    SELECT
        c.city,
        c.state,
        c.tier,
        b.population,
        b.median_income,
        ROUND(SAFE_DIVIDE(b.median_income, 12), 2) AS monthly_income,
        CASE 
            WHEN b.population >= 3000000 THEN "large"
            WHEN b.population >= 1000000 THEN "medium"
            ELSE "small"
        END AS metro_size
    FROM bronze b
    INNER JOIN cities c ON b.msa_id = c.cbsa_code
)

SELECT * FROM joined

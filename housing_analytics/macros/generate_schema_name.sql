{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

This makes dbt use your `+schema` value **exactly** with no prefix, giving you:
```
housing_bronze   ← bronze
housing_silver   ← silver
housing_gold     ← gold
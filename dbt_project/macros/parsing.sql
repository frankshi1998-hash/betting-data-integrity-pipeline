{% macro clean_text(expression) -%}
nullif(btrim({{ expression }}::text), '')
{%- endmacro %}

{% macro normalize_customer_name(expression) -%}
nullif(btrim(regexp_replace(upper({{ expression }}::text), '\s+', ' ', 'g')), '')
{%- endmacro %}

{% macro parse_money(expression) -%}
case
    when {{ clean_text(expression) }} is null then null
    when btrim({{ expression }}::text) ~ '^\(.*\)$' then
        -1 * nullif(
            regexp_replace(
                replace(trim(both '()' from btrim({{ expression }}::text)), ',', ''),
                '[^0-9.]',
                '',
                'g'
            ),
            ''
        )::numeric(14, 2)
    else
        nullif(
            regexp_replace(
                replace(btrim({{ expression }}::text), ',', ''),
                '[^0-9.-]',
                '',
                'g'
            ),
            ''
        )::numeric(14, 2)
end
{%- endmacro %}

{% macro parse_decimal(expression) -%}
case
    when {{ clean_text(expression) }} is null then null
    when btrim({{ expression }}::text) ~ '^\(.*\)$' then
        -1 * nullif(
            regexp_replace(
                replace(trim(both '()' from btrim({{ expression }}::text)), ',', ''),
                '[^0-9.]',
                '',
                'g'
            ),
            ''
        )::numeric(14, 4)
    else
        nullif(
            regexp_replace(
                replace(btrim({{ expression }}::text), ',', ''),
                '[^0-9.-]',
                '',
                'g'
            ),
            ''
        )::numeric(14, 4)
end
{%- endmacro %}

{% macro parse_integer(expression) -%}
nullif(
    regexp_replace(
        coalesce({{ clean_text(expression) }}, ''),
        '[^0-9-]',
        '',
        'g'
    ),
    ''
)::integer
{%- endmacro %}

{% macro parse_boolean_flag(expression) -%}
case upper(coalesce({{ clean_text(expression) }}, ''))
    when 'Y' then true
    when 'YES' then true
    when 'TRUE' then true
    when '1' then true
    when 'N' then false
    when 'NO' then false
    when 'FALSE' then false
    when '0' then false
    else null
end
{%- endmacro %}

{% macro parse_source_timestamp(date_expression, time_expression) -%}
case
    when {{ clean_text(date_expression) }} is null then null
    when {{ clean_text(time_expression) }} is null then ({{ clean_text(date_expression) }})::timestamp
    else ((({{ clean_text(date_expression) }})::timestamp)::date + ({{ clean_text(time_expression) }})::time)
end
{%- endmacro %}

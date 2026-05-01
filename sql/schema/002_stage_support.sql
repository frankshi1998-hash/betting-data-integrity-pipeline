create schema if not exists util;
create schema if not exists stage;

create or replace function util.clean_text(input_text text)
returns text
language sql
immutable
as $$
    select nullif(btrim(input_text), '')
$$;

create or replace function util.parse_money(input_text text)
returns numeric(14, 2)
language sql
immutable
as $$
    select
        case
            when util.clean_text(input_text) is null then null
            when btrim(input_text) ~ '^\(.*\)$' then
                -1 * nullif(
                    regexp_replace(
                        replace(trim(both '()' from btrim(input_text)), ',', ''),
                        '[^0-9.]',
                        '',
                        'g'
                    ),
                    ''
                )::numeric(14, 2)
            else
                nullif(
                    regexp_replace(
                        replace(btrim(input_text), ',', ''),
                        '[^0-9.-]',
                        '',
                        'g'
                    ),
                    ''
                )::numeric(14, 2)
        end
$$;

create or replace function util.parse_decimal(input_text text)
returns numeric(14, 4)
language sql
immutable
as $$
    select
        case
            when util.clean_text(input_text) is null then null
            when btrim(input_text) ~ '^\(.*\)$' then
                -1 * nullif(
                    regexp_replace(
                        replace(trim(both '()' from btrim(input_text)), ',', ''),
                        '[^0-9.]',
                        '',
                        'g'
                    ),
                    ''
                )::numeric(14, 4)
            else
                nullif(
                    regexp_replace(
                        replace(btrim(input_text), ',', ''),
                        '[^0-9.-]',
                        '',
                        'g'
                    ),
                    ''
                )::numeric(14, 4)
        end
$$;

create or replace function util.parse_integer(input_text text)
returns integer
language sql
immutable
as $$
    select
        nullif(
            regexp_replace(
                coalesce(util.clean_text(input_text), ''),
                '[^0-9-]',
                '',
                'g'
            ),
            ''
        )::integer
$$;

create or replace function util.parse_boolean_flag(input_text text)
returns boolean
language sql
immutable
as $$
    select
        case upper(coalesce(util.clean_text(input_text), ''))
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
$$;

create or replace function util.parse_source_timestamp(date_text text, time_text text)
returns timestamp
language sql
immutable
as $$
    select
        case
            when util.clean_text(date_text) is null then null
            when util.clean_text(time_text) is null then (util.clean_text(date_text))::timestamp
            else ((util.clean_text(date_text))::timestamp::date + (util.clean_text(time_text))::time)
        end
$$;

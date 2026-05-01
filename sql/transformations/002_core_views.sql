create schema if not exists core;

drop view if exists core.payouts;
drop view if exists core.bets;
drop view if exists core.events;
drop view if exists core.customers;

create view core.customers as
with normalized_customer_activity as (
    select
        md5(btrim(regexp_replace(upper(customer_name), '\s+', ' ', 'g'))) as customer_key,
        btrim(regexp_replace(upper(customer_name), '\s+', ' ', 'g')) as customer_name_normalized,
        customer_name as customer_name_raw,
        bookmaker_name,
        state_code,
        bet_placed_at,
        total_stake_amount,
        total_payout_amount
    from stage.bookmaker_bets_clean
    where customer_name is not null
)
select
    customer_key,
    customer_name_normalized,
    min(customer_name_raw) as customer_name_example,
    count(*) as bet_count,
    count(distinct bookmaker_name) as bookmaker_count,
    count(distinct state_code) as state_count,
    min(bet_placed_at) as first_bet_at,
    max(bet_placed_at) as last_bet_at,
    sum(coalesce(total_stake_amount, 0)) as total_stake_amount,
    sum(coalesce(total_payout_amount, 0)) as total_payout_amount
from normalized_customer_activity
group by customer_key, customer_name_normalized;

create view core.events as
with event_base as (
    select
        md5(
            concat_ws(
                '|',
                coalesce(event_category, ''),
                coalesce(venue_state_code, ''),
                coalesce(venue_name, ''),
                coalesce(event_scheduled_at::text, ''),
                coalesce(race_number::text, '')
            )
        ) as event_key,
        event_category,
        venue_name,
        venue_state_code,
        event_scheduled_at,
        race_number,
        runner_number,
        runner_name,
        bookmaker_name,
        total_stake_amount,
        total_payout_amount
    from stage.bookmaker_bets_clean
)
select
    event_key,
    event_category,
    venue_name,
    venue_state_code,
    event_scheduled_at,
    race_number,
    count(*) as bet_count,
    count(distinct runner_number) as distinct_runner_count,
    count(distinct bookmaker_name) as bookmaker_count,
    sum(coalesce(total_stake_amount, 0)) as total_stake_amount,
    sum(coalesce(total_payout_amount, 0)) as total_payout_amount
from event_base
group by
    event_key,
    event_category,
    venue_name,
    venue_state_code,
    event_scheduled_at,
    race_number;

create view core.bets as
with keyed_bets as (
    select
        md5(concat_ws('|', source_file, source_sheet, source_row_number::text)) as bet_record_key,
        md5(concat_ws('|', source_file, coalesce(source_uuid, ''), coalesce(ticket_no, ''))) as bet_business_key,
        md5(
            concat_ws(
                '|',
                coalesce(event_category, ''),
                coalesce(venue_state_code, ''),
                coalesce(venue_name, ''),
                coalesce(event_scheduled_at::text, ''),
                coalesce(race_number::text, '')
            )
        ) as event_key,
        case
            when customer_name is null then null
            else md5(btrim(regexp_replace(upper(customer_name), '\s+', ' ', 'g')))
        end as customer_key,
        md5(
            concat_ws(
                '|',
                coalesce(event_category, ''),
                coalesce(venue_state_code, ''),
                coalesce(venue_name, ''),
                coalesce(event_scheduled_at::text, ''),
                coalesce(race_number::text, ''),
                coalesce(runner_number::text, ''),
                coalesce(runner_name, '')
            )
        ) as selection_key,
        row_number() over (
            partition by source_file, source_uuid, ticket_no
            order by source_row_number, ingestion_id
        ) as duplicate_rank,
        s.*
    from stage.bookmaker_bets_clean s
)
select
    bet_record_key,
    bet_business_key,
    event_key,
    customer_key,
    selection_key,
    duplicate_rank,
    duplicate_rank > 1 as is_duplicate_bet_key,
    source_file,
    source_sheet,
    source_row_number,
    ingested_at,
    source_refid,
    source_uuid,
    license,
    bookmaker_name,
    location_name,
    state_code,
    area_name,
    wagering_provider,
    system_version,
    bet_placed_at,
    event_scheduled_at,
    ticket_no,
    event_category,
    sport_event_name,
    venue_name,
    venue_state_code,
    race_number,
    runner_number,
    runner_name,
    bet_type,
    bet_method,
    bet_details,
    customer_name,
    stake_win_amount,
    stake_place_amount,
    total_stake_amount,
    win_price,
    place_price,
    win_result,
    place_result,
    win_payout_amount,
    place_payout_amount,
    total_payout_amount,
    paid_status,
    is_cancelled,
    cancelled_at,
    is_betback,
    is_refunded,
    missing_refid_flag,
    missing_stake_flag,
    negative_stake_flag,
    raw_payload
from keyed_bets;

create view core.payouts as
select
    md5(concat_ws('|', bet_record_key, coalesce(total_payout_amount::text, ''))) as payout_record_key,
    bet_record_key,
    bet_business_key,
    event_key,
    customer_key,
    source_file,
    source_refid,
    source_uuid,
    ticket_no,
    bookmaker_name,
    bet_placed_at,
    event_scheduled_at,
    event_category,
    venue_name,
    venue_state_code,
    race_number,
    runner_number,
    runner_name,
    customer_name,
    paid_status,
    is_cancelled,
    is_refunded,
    is_duplicate_bet_key,
    win_result,
    place_result,
    win_payout_amount,
    place_payout_amount,
    total_payout_amount
from core.bets
where coalesce(total_payout_amount, 0) <> 0;

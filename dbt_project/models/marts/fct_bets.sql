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
            else md5({{ normalize_customer_name('customer_name') }})
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
    from {{ ref('stg_bookmaker_bets') }} s
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
from keyed_bets

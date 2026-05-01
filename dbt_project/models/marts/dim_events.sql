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
        bookmaker_name,
        total_stake_amount,
        total_payout_amount
    from {{ ref('stg_bookmaker_bets') }}
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
    race_number

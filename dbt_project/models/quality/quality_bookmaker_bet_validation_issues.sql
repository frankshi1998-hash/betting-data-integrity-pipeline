with duplicate_bet_keys as (
    select
        source_file,
        source_uuid,
        ticket_no,
        count(*) as duplicate_count
    from {{ ref('fct_bets') }}
    where source_uuid is not null
      and ticket_no is not null
    group by source_file, source_uuid, ticket_no
    having count(*) > 1
)

select
    'duplicate_bet_key'::text as issue_type,
    b.bet_record_key,
    b.bet_business_key,
    b.source_file,
    b.source_row_number,
    b.source_refid,
    b.source_uuid,
    b.ticket_no,
    b.bookmaker_name,
    b.bet_placed_at,
    b.total_stake_amount,
    b.total_payout_amount,
    'Duplicate source_uuid + ticket_no within the same source file'::text as issue_detail
from {{ ref('fct_bets') }} b
join duplicate_bet_keys d
  on d.source_file = b.source_file
 and d.source_uuid = b.source_uuid
 and d.ticket_no = b.ticket_no

union all

select
    'negative_total_stake'::text as issue_type,
    b.bet_record_key,
    b.bet_business_key,
    b.source_file,
    b.source_row_number,
    b.source_refid,
    b.source_uuid,
    b.ticket_no,
    b.bookmaker_name,
    b.bet_placed_at,
    b.total_stake_amount,
    b.total_payout_amount,
    'Total stake amount is below zero after parsing win/place stake values'::text as issue_detail
from {{ ref('fct_bets') }} b
where b.negative_stake_flag

union all

select
    'missing_event_timestamp'::text as issue_type,
    b.bet_record_key,
    b.bet_business_key,
    b.source_file,
    b.source_row_number,
    b.source_refid,
    b.source_uuid,
    b.ticket_no,
    b.bookmaker_name,
    b.bet_placed_at,
    b.total_stake_amount,
    b.total_payout_amount,
    'Event timestamp is null after combining event date and time fields'::text as issue_detail
from {{ ref('fct_bets') }} b
where b.event_scheduled_at is null

union all

select
    'cancelled_with_payout'::text as issue_type,
    b.bet_record_key,
    b.bet_business_key,
    b.source_file,
    b.source_row_number,
    b.source_refid,
    b.source_uuid,
    b.ticket_no,
    b.bookmaker_name,
    b.bet_placed_at,
    b.total_stake_amount,
    b.total_payout_amount,
    'Cancelled bet still shows a positive payout amount'::text as issue_detail
from {{ ref('fct_bets') }} b
where b.is_cancelled is true
  and coalesce(b.total_payout_amount, 0) > 0

union all

select
    'payout_without_stake'::text as issue_type,
    b.bet_record_key,
    b.bet_business_key,
    b.source_file,
    b.source_row_number,
    b.source_refid,
    b.source_uuid,
    b.ticket_no,
    b.bookmaker_name,
    b.bet_placed_at,
    b.total_stake_amount,
    b.total_payout_amount,
    'Positive payout amount exists while parsed stake amount is zero or null'::text as issue_detail
from {{ ref('fct_bets') }} b
where coalesce(b.total_stake_amount, 0) = 0
  and coalesce(b.total_payout_amount, 0) > 0

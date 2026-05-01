with daily_bets as (
    select
        source_file,
        bet_placed_at::date as report_date,
        count(*) as total_bet_rows,
        count(distinct bet_business_key) as distinct_bet_key_count,
        count(*) filter (where customer_key is not null) as named_customer_rows,
        count(*) filter (where is_cancelled is true) as cancelled_bet_rows,
        count(*) filter (where is_refunded is true) as refunded_bet_rows,
        sum(coalesce(total_stake_amount, 0)) as total_stake_amount,
        sum(coalesce(total_payout_amount, 0)) as total_payout_amount
    from {{ ref('fct_bets') }}
    group by source_file, bet_placed_at::date
),
duplicate_groups as (
    select
        source_file,
        report_date,
        count(*) as duplicate_bet_key_group_count,
        sum(duplicate_row_count - 1) as duplicate_extra_row_count
    from (
        select
            source_file,
            bet_placed_at::date as report_date,
            bet_business_key,
            count(*) as duplicate_row_count
        from {{ ref('fct_bets') }}
        group by source_file, bet_placed_at::date, bet_business_key
        having count(*) > 1
    ) duplicate_keys
    group by source_file, report_date
),
issue_counts as (
    select
        source_file,
        report_date,
        sum(issue_count) as total_issue_rows,
        sum(issue_count) filter (where issue_type = 'duplicate_bet_key') as duplicate_bet_key_issue_rows,
        sum(issue_count) filter (where issue_type = 'negative_total_stake') as negative_stake_issue_rows,
        sum(issue_count) filter (where issue_type = 'missing_event_timestamp') as missing_event_timestamp_issue_rows,
        sum(issue_count) filter (where issue_type = 'cancelled_with_payout') as cancelled_with_payout_issue_rows,
        sum(issue_count) filter (where issue_type = 'payout_without_stake') as payout_without_stake_issue_rows
    from {{ ref('rpt_daily_issue_summary') }}
    group by source_file, report_date
)

select
    b.source_file,
    b.report_date,
    b.total_bet_rows,
    b.distinct_bet_key_count,
    coalesce(d.duplicate_bet_key_group_count, 0) as duplicate_bet_key_group_count,
    coalesce(d.duplicate_extra_row_count, 0) as duplicate_extra_row_count,
    b.named_customer_rows,
    b.cancelled_bet_rows,
    b.refunded_bet_rows,
    coalesce(i.total_issue_rows, 0) as total_issue_rows,
    coalesce(i.duplicate_bet_key_issue_rows, 0) as duplicate_bet_key_issue_rows,
    coalesce(i.negative_stake_issue_rows, 0) as negative_stake_issue_rows,
    coalesce(i.missing_event_timestamp_issue_rows, 0) as missing_event_timestamp_issue_rows,
    coalesce(i.cancelled_with_payout_issue_rows, 0) as cancelled_with_payout_issue_rows,
    coalesce(i.payout_without_stake_issue_rows, 0) as payout_without_stake_issue_rows,
    b.total_stake_amount,
    b.total_payout_amount,
    b.total_stake_amount - b.total_payout_amount as net_revenue_amount,
    round(b.total_payout_amount / nullif(b.total_stake_amount, 0), 4) as payout_ratio,
    case when coalesce(i.total_issue_rows, 0) > 0 then 'review' else 'pass' end as reconciliation_status
from daily_bets b
left join duplicate_groups d
  on d.source_file = b.source_file
 and d.report_date = b.report_date
left join issue_counts i
  on i.source_file = b.source_file
 and i.report_date = b.report_date

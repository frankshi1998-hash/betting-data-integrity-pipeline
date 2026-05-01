create schema if not exists reporting;

drop view if exists reporting.daily_bookmaker_summary;
drop view if exists reporting.daily_issue_summary;
drop view if exists reporting.daily_reconciliation_summary;

create view reporting.daily_issue_summary as
select
    source_file,
    bet_placed_at::date as report_date,
    issue_type,
    count(*) as issue_count
from quality.bookmaker_bet_validation_issues
group by
    source_file,
    bet_placed_at::date,
    issue_type;

create view reporting.daily_reconciliation_summary as
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
    from core.bets
    group by
        source_file,
        bet_placed_at::date
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
        from core.bets
        group by
            source_file,
            bet_placed_at::date,
            bet_business_key
        having count(*) > 1
    ) duplicate_keys
    group by
        source_file,
        report_date
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
    from reporting.daily_issue_summary
    group by
        source_file,
        report_date
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
    round(
        b.total_payout_amount / nullif(b.total_stake_amount, 0),
        4
    ) as payout_ratio,
    case
        when coalesce(i.total_issue_rows, 0) > 0 then 'review'
        else 'pass'
    end as reconciliation_status
from daily_bets b
left join duplicate_groups d
    on d.source_file = b.source_file
   and d.report_date = b.report_date
left join issue_counts i
    on i.source_file = b.source_file
   and i.report_date = b.report_date;

create view reporting.daily_bookmaker_summary as
with duplicate_rows as (
    select
        bookmaker_name,
        bet_placed_at::date as report_date,
        count(*) as duplicate_extra_row_count
    from core.bets
    where is_duplicate_bet_key
    group by
        bookmaker_name,
        bet_placed_at::date
)
select
    b.bookmaker_name,
    b.bet_placed_at::date as report_date,
    count(*) as total_bet_rows,
    count(distinct b.bet_business_key) as distinct_bet_key_count,
    count(*) filter (where b.customer_key is not null) as named_customer_rows,
    count(*) filter (where b.is_cancelled is true) as cancelled_bet_rows,
    count(*) filter (where b.is_refunded is true) as refunded_bet_rows,
    coalesce(d.duplicate_extra_row_count, 0) as duplicate_extra_row_count,
    sum(coalesce(b.total_stake_amount, 0)) as total_stake_amount,
    sum(coalesce(b.total_payout_amount, 0)) as total_payout_amount,
    sum(coalesce(b.total_stake_amount, 0)) - sum(coalesce(b.total_payout_amount, 0)) as net_revenue_amount
from core.bets b
left join duplicate_rows d
    on d.bookmaker_name = b.bookmaker_name
   and d.report_date = b.bet_placed_at::date
group by
    b.bookmaker_name,
    b.bet_placed_at::date,
    d.duplicate_extra_row_count;

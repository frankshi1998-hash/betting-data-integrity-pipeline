with bookmaker_metrics as (
    select
        bookmaker_name,
        report_date,
        total_bet_rows,
        duplicate_extra_row_count,
        total_stake_amount,
        total_payout_amount,
        net_revenue_amount,
        round(duplicate_extra_row_count::numeric / nullif(total_bet_rows, 0), 4) as duplicate_ratio,
        round(total_payout_amount / nullif(total_stake_amount, 0), 4) as payout_ratio
    from {{ ref('rpt_daily_bookmaker_summary') }}
),
bookmaker_alerts as (
    select
        null::text as source_file,
        report_date,
        'bookmaker_day'::text as alert_scope,
        bookmaker_name,
        case when duplicate_ratio >= 0.25 then 'critical' else 'high' end as severity,
        'bookmaker_duplicate_ratio_spike'::text as alert_type,
        'integrity_ops'::text as alert_owner,
        concat('Bookmaker duplicate ratio ', round(duplicate_ratio * 100, 2), '% exceeded threshold for ', bookmaker_name) as alert_message,
        total_bet_rows,
        duplicate_extra_row_count,
        duplicate_ratio,
        null::bigint as negative_stake_issue_rows,
        null::numeric as negative_stake_ratio,
        duplicate_extra_row_count as total_issue_rows,
        total_stake_amount,
        total_payout_amount,
        net_revenue_amount,
        payout_ratio
    from bookmaker_metrics
    where total_bet_rows >= 100
      and duplicate_extra_row_count >= 25
      and duplicate_ratio >= 0.10

    union all

    select
        null::text as source_file,
        report_date,
        'bookmaker_day'::text as alert_scope,
        bookmaker_name,
        case when payout_ratio >= 1.20 then 'critical' else 'high' end as severity,
        'bookmaker_loss_day'::text as alert_type,
        'finance_recon'::text as alert_owner,
        concat('Bookmaker payout ratio ', round(payout_ratio, 4), ' exceeded loss threshold for ', bookmaker_name) as alert_message,
        total_bet_rows,
        duplicate_extra_row_count,
        duplicate_ratio,
        null::bigint as negative_stake_issue_rows,
        null::numeric as negative_stake_ratio,
        duplicate_extra_row_count as total_issue_rows,
        total_stake_amount,
        total_payout_amount,
        net_revenue_amount,
        payout_ratio
    from bookmaker_metrics
    where total_stake_amount >= 100000
      and payout_ratio >= 1.05
)

select
    md5(concat_ws('|', alert_scope, coalesce(source_file, ''), report_date::text, alert_type, bookmaker_name)) as alert_id,
    alert_scope,
    report_date,
    source_file,
    bookmaker_name,
    severity,
    alert_type,
    alert_owner,
    alert_message,
    total_bet_rows,
    duplicate_extra_row_count,
    duplicate_ratio,
    negative_stake_issue_rows,
    negative_stake_ratio,
    total_issue_rows,
    total_stake_amount,
    total_payout_amount,
    net_revenue_amount,
    payout_ratio
from bookmaker_alerts

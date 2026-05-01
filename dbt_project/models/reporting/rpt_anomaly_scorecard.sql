with alert_counts as (
    select
        source_file,
        report_date,
        count(*) as alert_count,
        count(*) filter (where severity = 'critical') as critical_alert_count,
        count(*) filter (where severity = 'high') as high_alert_count,
        count(*) filter (where severity = 'medium') as medium_alert_count
    from {{ ref('rpt_alert_feed') }}
    where alert_scope = 'source_day'
    group by source_file, report_date
),
base_metrics as (
    select
        r.source_file,
        r.report_date,
        r.total_bet_rows,
        r.distinct_bet_key_count,
        r.duplicate_extra_row_count,
        r.total_issue_rows,
        r.negative_stake_issue_rows,
        r.missing_event_timestamp_issue_rows,
        r.cancelled_with_payout_issue_rows,
        r.payout_without_stake_issue_rows,
        r.total_stake_amount,
        r.total_payout_amount,
        r.net_revenue_amount,
        r.payout_ratio,
        r.reconciliation_status,
        coalesce(a.alert_count, 0) as alert_count,
        coalesce(a.critical_alert_count, 0) as critical_alert_count,
        coalesce(a.high_alert_count, 0) as high_alert_count,
        coalesce(a.medium_alert_count, 0) as medium_alert_count,
        round(coalesce(r.duplicate_extra_row_count::numeric / nullif(r.total_bet_rows, 0), 0), 4) as duplicate_ratio,
        round(coalesce(r.negative_stake_issue_rows::numeric / nullif(r.total_bet_rows, 0), 0), 4) as negative_stake_ratio,
        round(coalesce(r.total_issue_rows::numeric / nullif(r.total_bet_rows, 0), 0), 4) as issue_ratio
    from {{ ref('rpt_daily_reconciliation_summary') }} r
    left join alert_counts a
      on a.source_file = r.source_file
     and a.report_date = r.report_date
),
score_components as (
    select
        *,
        least(30::numeric, round(duplicate_ratio * 200, 2)) as duplicate_component_score,
        least(25::numeric, round(negative_stake_ratio * 150, 2)) as negative_stake_component_score,
        least(20::numeric, round(greatest(coalesce(payout_ratio, 0) - 1, 0) * 100, 2)) as payout_loss_component_score,
        least(15::numeric, round(issue_ratio * 50, 2)) as issue_density_component_score,
        least(
            10::numeric,
            (critical_alert_count * 10 + high_alert_count * 6 + medium_alert_count * 3)::numeric
        ) as alert_severity_component_score
    from base_metrics
),
scored as (
    select
        *,
        least(
            100::numeric,
            duplicate_component_score
            + negative_stake_component_score
            + payout_loss_component_score
            + issue_density_component_score
            + alert_severity_component_score
        ) as anomaly_score
    from score_components
)

select
    md5(concat_ws('|', source_file, report_date::text)) as anomaly_id,
    source_file,
    report_date,
    anomaly_score,
    case
        when anomaly_score >= 80 then 'critical'
        when anomaly_score >= 60 then 'high'
        when anomaly_score >= 35 then 'medium'
        when anomaly_score >= 15 then 'low'
        else 'normal'
    end as risk_band,
    case
        when anomaly_score = 0 then 'none'
        when greatest(
            duplicate_component_score,
            negative_stake_component_score,
            payout_loss_component_score,
            issue_density_component_score,
            alert_severity_component_score
        ) = duplicate_component_score then 'duplicate_pressure'
        when greatest(
            duplicate_component_score,
            negative_stake_component_score,
            payout_loss_component_score,
            issue_density_component_score,
            alert_severity_component_score
        ) = negative_stake_component_score then 'negative_stake_pressure'
        when greatest(
            duplicate_component_score,
            negative_stake_component_score,
            payout_loss_component_score,
            issue_density_component_score,
            alert_severity_component_score
        ) = payout_loss_component_score then 'payout_loss_pressure'
        when greatest(
            duplicate_component_score,
            negative_stake_component_score,
            payout_loss_component_score,
            issue_density_component_score,
            alert_severity_component_score
        ) = issue_density_component_score then 'issue_density'
        else 'alert_severity'
    end as primary_driver,
    case
        when anomaly_score >= 80 then 'Immediate integrity and finance review'
        when anomaly_score >= 60 then 'Prioritise for same-day investigation'
        when anomaly_score >= 35 then 'Review during daily reconciliation'
        when anomaly_score >= 15 then 'Monitor for repeated pattern'
        else 'No action required'
    end as recommended_action,
    total_bet_rows,
    distinct_bet_key_count,
    duplicate_extra_row_count,
    total_issue_rows,
    negative_stake_issue_rows,
    missing_event_timestamp_issue_rows,
    cancelled_with_payout_issue_rows,
    payout_without_stake_issue_rows,
    alert_count,
    critical_alert_count,
    high_alert_count,
    medium_alert_count,
    duplicate_ratio,
    negative_stake_ratio,
    issue_ratio,
    total_stake_amount,
    total_payout_amount,
    net_revenue_amount,
    payout_ratio,
    duplicate_component_score,
    negative_stake_component_score,
    payout_loss_component_score,
    issue_density_component_score,
    alert_severity_component_score,
    reconciliation_status
from scored

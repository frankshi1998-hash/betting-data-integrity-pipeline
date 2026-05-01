select
    *
from {{ ref('rpt_source_day_alerts') }}
where (
        alert_type = 'duplicate_ratio_spike'
    and not (
        total_bet_rows >= 500
        and duplicate_extra_row_count >= 100
        and duplicate_ratio >= 0.10
        and (
            (severity = 'critical' and duplicate_ratio >= 0.25)
            or (severity = 'high' and duplicate_ratio < 0.25)
        )
        and alert_owner = 'integrity_ops'
    )
)
or (
        alert_type = 'negative_stake_spike'
    and not (
        total_bet_rows >= 100
        and negative_stake_issue_rows >= 50
        and negative_stake_ratio >= 0.10
        and (
            (severity = 'critical' and negative_stake_ratio >= 0.50)
            or (severity = 'high' and negative_stake_ratio >= 0.25 and negative_stake_ratio < 0.50)
            or (severity = 'medium' and negative_stake_ratio >= 0.10 and negative_stake_ratio < 0.25)
        )
        and alert_owner = 'reconciliation_ops'
    )
)
or (
        alert_type = 'loss_day_payout_ratio'
    and not (
        total_stake_amount >= 50000
        and payout_ratio >= 1.05
        and (
            (severity = 'critical' and payout_ratio >= 1.20)
            or (severity = 'high' and payout_ratio < 1.20)
        )
        and alert_owner = 'finance_recon'
    )
)
or alert_scope <> 'source_day'
or source_file is null
or bookmaker_name is not null

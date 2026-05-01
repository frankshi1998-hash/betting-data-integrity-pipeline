select
    *
from {{ ref('rpt_bookmaker_day_alerts') }}
where (
        alert_type = 'bookmaker_duplicate_ratio_spike'
    and not (
        total_bet_rows >= 100
        and duplicate_extra_row_count >= 25
        and duplicate_ratio >= 0.10
        and (
            (severity = 'critical' and duplicate_ratio >= 0.25)
            or (severity = 'high' and duplicate_ratio < 0.25)
        )
        and alert_owner = 'integrity_ops'
    )
)
or (
        alert_type = 'bookmaker_loss_day'
    and not (
        total_stake_amount >= 100000
        and payout_ratio >= 1.05
        and (
            (severity = 'critical' and payout_ratio >= 1.20)
            or (severity = 'high' and payout_ratio < 1.20)
        )
        and alert_owner = 'finance_recon'
    )
)
or alert_scope <> 'bookmaker_day'
or source_file is not null
or bookmaker_name is null

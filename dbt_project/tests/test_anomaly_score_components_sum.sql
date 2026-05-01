select
    anomaly_id,
    anomaly_score,
    duplicate_component_score,
    negative_stake_component_score,
    payout_loss_component_score,
    issue_density_component_score,
    alert_severity_component_score
from {{ ref('rpt_anomaly_scorecard') }}
where anomaly_score <> least(
    100::numeric,
    duplicate_component_score
    + negative_stake_component_score
    + payout_loss_component_score
    + issue_density_component_score
    + alert_severity_component_score
)

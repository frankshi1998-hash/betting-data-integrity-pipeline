select
    anomaly_id,
    anomaly_score,
    risk_band
from {{ ref('rpt_anomaly_scorecard') }}
where (anomaly_score >= 80 and risk_band <> 'critical')
   or (anomaly_score >= 60 and anomaly_score < 80 and risk_band <> 'high')
   or (anomaly_score >= 35 and anomaly_score < 60 and risk_band <> 'medium')
   or (anomaly_score >= 15 and anomaly_score < 35 and risk_band <> 'low')
   or (anomaly_score < 15 and risk_band <> 'normal')

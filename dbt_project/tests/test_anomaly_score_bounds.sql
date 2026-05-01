select
    anomaly_id,
    anomaly_score
from {{ ref('rpt_anomaly_scorecard') }}
where anomaly_score < 0
   or anomaly_score > 100

select
    report_date,
    alert_scope,
    severity,
    alert_type,
    count(*) as alert_count
from {{ ref('rpt_alert_feed') }}
group by report_date, alert_scope, severity, alert_type

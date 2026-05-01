with feed as (
    select
        report_date,
        alert_scope,
        severity,
        alert_type,
        count(*) as alert_count
    from {{ ref('rpt_alert_feed') }}
    group by report_date, alert_scope, severity, alert_type
),
summary as (
    select
        report_date,
        alert_scope,
        severity,
        alert_type,
        alert_count
    from {{ ref('rpt_alert_summary') }}
)
select
    coalesce(feed.report_date, summary.report_date) as report_date,
    coalesce(feed.alert_scope, summary.alert_scope) as alert_scope,
    coalesce(feed.severity, summary.severity) as severity,
    coalesce(feed.alert_type, summary.alert_type) as alert_type,
    feed.alert_count as feed_alert_count,
    summary.alert_count as summary_alert_count
from feed
full outer join summary
    on feed.report_date = summary.report_date
   and feed.alert_scope = summary.alert_scope
   and feed.severity = summary.severity
   and feed.alert_type = summary.alert_type
where coalesce(feed.alert_count, -1) <> coalesce(summary.alert_count, -1)

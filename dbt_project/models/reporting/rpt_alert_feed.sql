select * from {{ ref('rpt_source_day_alerts') }}
union all
select * from {{ ref('rpt_bookmaker_day_alerts') }}

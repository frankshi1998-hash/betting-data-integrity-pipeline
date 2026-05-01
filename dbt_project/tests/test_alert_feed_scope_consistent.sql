select
    *
from {{ ref('rpt_alert_feed') }}
where severity not in ('critical', 'high', 'medium')
   or (alert_scope = 'source_day' and (source_file is null or bookmaker_name is not null))
   or (alert_scope = 'bookmaker_day' and (source_file is not null or bookmaker_name is null))
   or alert_scope not in ('source_day', 'bookmaker_day')

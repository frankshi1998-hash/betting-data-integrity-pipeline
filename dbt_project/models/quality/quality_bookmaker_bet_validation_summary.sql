select
    issue_type,
    count(*) as issue_count
from {{ ref('quality_bookmaker_bet_validation_issues') }}
group by issue_type

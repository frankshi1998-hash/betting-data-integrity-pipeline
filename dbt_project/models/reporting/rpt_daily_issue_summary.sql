select
    source_file,
    bet_placed_at::date as report_date,
    issue_type,
    count(*) as issue_count
from {{ ref('quality_bookmaker_bet_validation_issues') }}
group by source_file, bet_placed_at::date, issue_type

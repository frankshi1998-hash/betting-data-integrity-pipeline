select
    *
from {{ ref('rpt_daily_reconciliation_summary') }}
where reconciliation_status not in ('pass', 'review')
   or (reconciliation_status = 'pass' and total_issue_rows <> 0)
   or (reconciliation_status = 'review' and total_issue_rows = 0)
   or (total_stake_amount = 0 and payout_ratio is not null)
   or (total_stake_amount <> 0 and payout_ratio is null)

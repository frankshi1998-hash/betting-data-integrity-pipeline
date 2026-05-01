select
    *
from {{ ref('rpt_daily_reconciliation_summary') }}
where distinct_bet_key_count > total_bet_rows
   or duplicate_bet_key_group_count > total_bet_rows
   or duplicate_extra_row_count > total_bet_rows
   or named_customer_rows > total_bet_rows
   or cancelled_bet_rows > total_bet_rows
   or refunded_bet_rows > total_bet_rows
   or duplicate_bet_key_issue_rows > total_bet_rows
   or negative_stake_issue_rows > total_bet_rows
   or missing_event_timestamp_issue_rows > total_bet_rows
   or cancelled_with_payout_issue_rows > total_bet_rows
   or payout_without_stake_issue_rows > total_bet_rows
   or total_issue_rows < (
        coalesce(duplicate_bet_key_issue_rows, 0)
      + coalesce(negative_stake_issue_rows, 0)
      + coalesce(missing_event_timestamp_issue_rows, 0)
      + coalesce(cancelled_with_payout_issue_rows, 0)
      + coalesce(payout_without_stake_issue_rows, 0)
   )

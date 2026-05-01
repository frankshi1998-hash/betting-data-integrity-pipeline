# EOD Betting Integrity Report

Generated at: `2026-03-01T18:30:00`

## Executive Summary
- Source-days reviewed: `1`
- Total bet rows: `600`
- Source-days requiring review: `1`
- High-risk source-days: `1`
- Alerts generated: `3`
- Quality issue rows: `341`
- Max anomaly score: `95.25`
- Total stake: `$60,088.00`
- Total payout: `$94,670.40`
- Net revenue: `$-34,582.40`

## Risk Bands
| risk_band | source_day_count | max_anomaly_score |
| --- | --- | --- |
| critical | 1 | 95.25 |

## Top Anomaly Priorities
| report_date | source_file | anomaly_score | risk_band | primary_driver | recommended_action |
| --- | --- | --- | --- | --- | --- |
| 2026-03-01 | demo_bookmaker_bet_dump.xlsx | 95.25 | critical | duplicate_pressure | Immediate integrity and finance review |

## Alert Summary
| severity | alert_type | alert_count |
| --- | --- | --- |
| critical | loss_day_payout_ratio | 1 |
| high | duplicate_ratio_spike | 1 |
| medium | negative_stake_spike | 1 |

## Quality Issue Summary
| issue_type | issue_count |
| --- | --- |
| duplicate_bet_key | 242 |
| negative_total_stake | 81 |

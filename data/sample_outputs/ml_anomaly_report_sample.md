# ML Anomaly Model Report

Generated at: `2026-05-02T00:08:20`

## Model Summary

- Model: `isolation_forest_source_day_v1`
- Rows scored: `1`
- Model outliers: `1`
- Max ML anomaly score: `100.00`

The model is an unsupervised Isolation Forest over source-day reconciliation features. It is a secondary triage signal; the explainable rule scorecard remains the operational source of truth.

## Features

rule anomaly score, duplicate pressure, negative stake pressure, quality issue density, payout ratio pressure, bet volume, issue volume, alert volume, critical alert volume, net revenue movement

## Top ML Anomaly Priorities

| report_date | source_file | ml_score | ml_risk | rule_score | rule_risk | model_driver | action |
| --- | --- | ---: | --- | ---: | --- | --- | --- |
| 2026-03-01 | demo_bookmaker_bet_dump.xlsx | 100.00 | critical | 95.25 | critical | net revenue movement | Investigate immediately; ML agrees with rule-based anomaly pressure |

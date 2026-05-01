from __future__ import annotations

import argparse
import csv
import html
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
DASHBOARD_FILENAME = "integrity_dashboard.html"


@dataclass(frozen=True)
class DashboardContext:
    generated_at: datetime
    source_day_count: int
    total_bet_rows: int
    review_source_day_count: int
    high_risk_source_day_count: int
    alert_count: int
    ml_outlier_count: int
    max_rule_score: float
    max_ml_score: float
    total_stake_amount: float
    total_payout_amount: float
    net_revenue_amount: float
    top_anomalies: list[dict[str, Any]]
    top_ml_anomalies: list[dict[str, Any]]
    alert_summary: list[dict[str, Any]]
    issue_summary: list[dict[str, Any]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a static HTML dashboard from reporting artifacts."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory containing generated reporting CSVs.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional dashboard HTML path. Defaults to <output-dir>/integrity_dashboard.html.",
    )
    return parser.parse_args(argv)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def to_int(value: Any) -> int:
    return int(round(to_float(value)))


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def number(value: float | int) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.2f}"


def risk_class(risk_band: str) -> str:
    return {
        "critical": "risk-critical",
        "high": "risk-high",
        "medium": "risk-medium",
        "low": "risk-low",
    }.get(str(risk_band).lower(), "risk-normal")


def summarize_alerts(alert_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for row in alert_rows:
        key = (row.get("severity", "unknown"), row.get("alert_type", "unknown"))
        counts[key] = counts.get(key, 0) + 1

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return [
        {"severity": severity, "alert_type": alert_type, "alert_count": count}
        for (severity, alert_type), count in sorted(
            counts.items(),
            key=lambda item: (
                severity_order.get(item[0][0], 9),
                item[0][1],
            ),
        )
    ]


def summarize_issues(issue_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in issue_rows:
        issue_type = row.get("issue_type", "unknown")
        counts[issue_type] = counts.get(issue_type, 0) + to_int(row.get("issue_count"))

    return [
        {"issue_type": issue_type, "issue_count": count}
        for issue_type, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def build_context(output_dir: Path, generated_at: datetime | None = None) -> DashboardContext:
    reconciliation_rows = read_csv_rows(output_dir / "daily_reconciliation_summary.csv")
    anomaly_rows = read_csv_rows(output_dir / "anomaly_scorecard.csv")
    alert_rows = read_csv_rows(output_dir / "alert_feed.csv")
    issue_rows = read_csv_rows(output_dir / "daily_issue_summary.csv")
    ml_rows = read_csv_rows(output_dir / "ml_anomaly_scores.csv")

    top_anomalies = sorted(
        anomaly_rows,
        key=lambda row: to_float(row.get("anomaly_score")),
        reverse=True,
    )[:5]
    top_ml_anomalies = sorted(
        ml_rows,
        key=lambda row: to_float(row.get("ml_anomaly_score")),
        reverse=True,
    )[:5]

    return DashboardContext(
        generated_at=generated_at or datetime.now(),
        source_day_count=len(reconciliation_rows),
        total_bet_rows=sum(to_int(row.get("total_bet_rows")) for row in reconciliation_rows),
        review_source_day_count=sum(
            1 for row in reconciliation_rows if row.get("reconciliation_status") == "review"
        ),
        high_risk_source_day_count=sum(
            1 for row in anomaly_rows if row.get("risk_band") in {"critical", "high"}
        ),
        alert_count=len(alert_rows),
        ml_outlier_count=sum(
            1 for row in ml_rows if str(row.get("model_outlier_flag", "")).lower() == "true"
        ),
        max_rule_score=max((to_float(row.get("anomaly_score")) for row in anomaly_rows), default=0.0),
        max_ml_score=max((to_float(row.get("ml_anomaly_score")) for row in ml_rows), default=0.0),
        total_stake_amount=sum(to_float(row.get("total_stake_amount")) for row in reconciliation_rows),
        total_payout_amount=sum(to_float(row.get("total_payout_amount")) for row in reconciliation_rows),
        net_revenue_amount=sum(to_float(row.get("net_revenue_amount")) for row in reconciliation_rows),
        top_anomalies=top_anomalies,
        top_ml_anomalies=top_ml_anomalies,
        alert_summary=summarize_alerts(alert_rows)[:8],
        issue_summary=summarize_issues(issue_rows)[:8],
    )


def escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def render_metric_card(label: str, value: str, note: str) -> str:
    return (
        '<article class="metric-card">'
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(value)}</strong>"
        f"<small>{escape(note)}</small>"
        "</article>"
    )


def render_anomaly_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<tr><td colspan="6">No anomaly rows found.</td></tr>'

    rendered_rows = []
    for row in rows:
        rendered_rows.append(
            "<tr>"
            f"<td>{escape(row.get('report_date'))}</td>"
            f"<td>{escape(row.get('source_file'))}</td>"
            f"<td>{float(to_float(row.get('anomaly_score'))):.2f}</td>"
            f'<td><span class="pill {risk_class(row.get("risk_band", ""))}">{escape(row.get("risk_band"))}</span></td>'
            f"<td>{escape(row.get('primary_driver'))}</td>"
            f"<td>{escape(row.get('recommended_action'))}</td>"
            "</tr>"
        )
    return "\n".join(rendered_rows)


def render_ml_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<tr><td colspan="6">ML scores were not generated for this run.</td></tr>'

    rendered_rows = []
    for row in rows:
        flag = "outlier" if str(row.get("model_outlier_flag", "")).lower() == "true" else "inlier"
        rendered_rows.append(
            "<tr>"
            f"<td>{escape(row.get('report_date'))}</td>"
            f"<td>{escape(row.get('source_file'))}</td>"
            f"<td>{float(to_float(row.get('ml_anomaly_score'))):.2f}</td>"
            f'<td><span class="pill {risk_class(row.get("ml_risk_band", ""))}">{escape(row.get("ml_risk_band"))}</span></td>'
            f"<td>{escape(row.get('model_driver'))}</td>"
            f"<td>{flag}</td>"
            "</tr>"
        )
    return "\n".join(rendered_rows)


def render_summary_list(rows: list[dict[str, Any]], label_key: str, count_key: str) -> str:
    if not rows:
        return "<li>No rows found.</li>"

    return "\n".join(
        f"<li><span>{escape(row.get(label_key))}</span><strong>{number(to_int(row.get(count_key)))}</strong></li>"
        for row in rows
    )


def render_dashboard_html(context: DashboardContext) -> str:
    metric_cards = "\n".join(
        [
            render_metric_card("Source-days", number(context.source_day_count), "reporting grain"),
            render_metric_card("Bet rows", number(context.total_bet_rows), "loaded and reconciled"),
            render_metric_card("Review days", number(context.review_source_day_count), "needs finance review"),
            render_metric_card("High risk", number(context.high_risk_source_day_count), "critical or high"),
            render_metric_card("Alerts", number(context.alert_count), "rule-based events"),
            render_metric_card("ML outliers", number(context.ml_outlier_count), "model-prioritized"),
            render_metric_card("Max rule score", number(context.max_rule_score), "0 to 100 scorecard"),
            render_metric_card("Max ML score", number(context.max_ml_score), "0 to 100 model score"),
        ]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Betting Integrity Pipeline Dashboard</title>
  <style>
    :root {{
      --ink: #1e2117;
      --muted: #68705a;
      --paper: #fbf5e8;
      --panel: rgba(255, 252, 243, 0.86);
      --ember: #c94f2d;
      --moss: #496b4a;
      --gold: #d7a441;
      --blue: #315f79;
      --line: rgba(30, 33, 23, 0.14);
      --shadow: 0 24px 70px rgba(62, 49, 27, 0.18);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Aptos", "Trebuchet MS", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(215, 164, 65, 0.35), transparent 34rem),
        radial-gradient(circle at 92% 12%, rgba(73, 107, 74, 0.23), transparent 26rem),
        linear-gradient(135deg, #f6ead3 0%, #fbf5e8 45%, #e9efe4 100%);
      min-height: 100vh;
    }}

    .shell {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 42px 0;
    }}

    .hero {{
      position: relative;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 34px;
      padding: 42px;
      background: linear-gradient(135deg, rgba(255, 252, 243, 0.94), rgba(232, 239, 225, 0.76));
      box-shadow: var(--shadow);
    }}

    .hero::after {{
      content: "";
      position: absolute;
      right: -88px;
      top: -88px;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      border: 38px solid rgba(201, 79, 45, 0.13);
    }}

    .eyebrow {{
      color: var(--moss);
      font-size: 0.78rem;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      font-weight: 800;
    }}

    h1, h2 {{
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
      line-height: 1;
      margin: 0;
    }}

    h1 {{
      max-width: 760px;
      margin-top: 16px;
      font-size: clamp(2.6rem, 8vw, 6.4rem);
      letter-spacing: -0.075em;
    }}

    .hero p {{
      max-width: 710px;
      margin: 22px 0 0;
      color: var(--muted);
      font-size: 1.1rem;
      line-height: 1.7;
    }}

    .money-strip {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin-top: 30px;
    }}

    .money-strip div, .metric-card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: 0 12px 34px rgba(62, 49, 27, 0.08);
    }}

    .money-strip div {{
      border-radius: 22px;
      padding: 18px;
    }}

    .money-strip span, .metric-card span {{
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-weight: 800;
    }}

    .money-strip strong {{
      display: block;
      margin-top: 8px;
      font-size: 1.55rem;
    }}

    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin: 26px 0;
    }}

    .metric-card {{
      border-radius: 24px;
      padding: 20px;
    }}

    .metric-card strong {{
      display: block;
      margin-top: 12px;
      font-size: 2rem;
      letter-spacing: -0.04em;
    }}

    .metric-card small {{
      display: block;
      color: var(--muted);
      margin-top: 8px;
    }}

    .grid {{
      display: grid;
      grid-template-columns: 1.35fr 0.65fr;
      gap: 18px;
      margin-top: 18px;
    }}

    .panel {{
      border-radius: 28px;
      padding: 24px;
      overflow: hidden;
    }}

    .panel h2 {{
      font-size: 1.75rem;
      letter-spacing: -0.04em;
      margin-bottom: 18px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
    }}

    th {{
      color: var(--muted);
      text-align: left;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-size: 0.72rem;
    }}

    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 12px 10px;
      vertical-align: top;
    }}

    .pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 10px;
      color: #fff;
      font-weight: 800;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .risk-critical {{ background: var(--ember); }}
    .risk-high {{ background: #a65b2a; }}
    .risk-medium {{ background: var(--gold); color: var(--ink); }}
    .risk-low {{ background: var(--blue); }}
    .risk-normal {{ background: var(--moss); }}

    .rank-list {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 10px;
    }}

    .rank-list li {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 0;
      border-bottom: 1px solid var(--line);
    }}

    .rank-list span {{
      color: var(--muted);
    }}

    .footer {{
      margin-top: 24px;
      color: var(--muted);
      font-size: 0.88rem;
      text-align: center;
    }}

    @media (max-width: 860px) {{
      .hero {{ padding: 28px; border-radius: 24px; }}
      .money-strip, .metric-grid, .grid {{ grid-template-columns: 1fr; }}
      table {{ font-size: 0.82rem; }}
      th, td {{ padding: 10px 6px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <span class="eyebrow">Betting Data Integrity Pipeline</span>
      <h1>Operational risk, reconciled.</h1>
      <p>This dashboard summarizes raw betting dumps after ingestion, SQL validation, rule-based anomaly scoring, ML outlier detection, and end-of-day reporting.</p>
      <div class="money-strip">
        <div><span>Total stake</span><strong>{escape(money(context.total_stake_amount))}</strong></div>
        <div><span>Total payout</span><strong>{escape(money(context.total_payout_amount))}</strong></div>
        <div><span>Net revenue</span><strong>{escape(money(context.net_revenue_amount))}</strong></div>
      </div>
    </section>

    <section class="metric-grid">
      {metric_cards}
    </section>

    <section class="grid">
      <article class="panel">
        <h2>Rule-Based Anomaly Priorities</h2>
        <table>
          <thead><tr><th>Date</th><th>Source</th><th>Score</th><th>Risk</th><th>Driver</th><th>Action</th></tr></thead>
          <tbody>{render_anomaly_rows(context.top_anomalies)}</tbody>
        </table>
      </article>
      <aside class="panel">
        <h2>Alert Mix</h2>
        <ul class="rank-list">
          {render_summary_list(context.alert_summary, "alert_type", "alert_count")}
        </ul>
      </aside>
    </section>

    <section class="grid">
      <article class="panel">
        <h2>ML Outlier Priorities</h2>
        <table>
          <thead><tr><th>Date</th><th>Source</th><th>Score</th><th>Risk</th><th>Driver</th><th>Flag</th></tr></thead>
          <tbody>{render_ml_rows(context.top_ml_anomalies)}</tbody>
        </table>
      </article>
      <aside class="panel">
        <h2>Quality Issue Mix</h2>
        <ul class="rank-list">
          {render_summary_list(context.issue_summary, "issue_type", "issue_count")}
        </ul>
      </aside>
    </section>

    <p class="footer">Generated {escape(context.generated_at.isoformat(timespec="seconds"))}. Static artifact; no external services required.</p>
  </main>
</body>
</html>
"""


def generate_dashboard(output_dir: Path, output_path: Path | None = None) -> Path:
    dashboard_path = output_path or output_dir / DASHBOARD_FILENAME
    context = build_context(output_dir)
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(render_dashboard_html(context), encoding="utf-8")
    return dashboard_path


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    dashboard_path = generate_dashboard(args.output_dir, args.output_path)
    print(f"Wrote integrity dashboard to {dashboard_path}")


if __name__ == "__main__":
    main()

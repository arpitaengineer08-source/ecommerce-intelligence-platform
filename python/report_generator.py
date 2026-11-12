"""Automated reporting: business_insights.md, weekly_summary.md and an executive PDF."""
from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import REPORTS  # noqa: E402
from python.database_loader import Database, run_named_query  # noqa: E402


def kpis(db: Database) -> dict:
    k = db.query("""SELECT SUM(item_revenue) revenue, COUNT(*) orders, COUNT(DISTINCT customer_unique_id) customers,
                           AVG(avg_review_score) review, 100.0*AVG(is_late) late_pct, AVG(delivery_days) delivery_days
                    FROM analytics.vw_delivered_orders""").iloc[0]
    tot = db.query("SELECT COUNT(*) n, COUNT(*) FILTER (WHERE order_status IN ('canceled','unavailable')) c FROM analytics.fact_orders").iloc[0]
    rep = run_named_query(db, "cus_repeat_rate").iloc[0]
    return {"revenue": float(k.revenue), "orders": int(k.orders), "customers": int(k.customers), "aov": float(k.revenue / k.orders),
            "review": float(k.review), "late_pct": float(k.late_pct), "delivery_days": float(k.delivery_days),
            "cancel_pct": float(tot.c / tot.n * 100), "repeat_pct": float(rep.repeat_customer_pct)}


def write_business_insights(recs: list[dict], k: dict, source: str, fc_metrics=None) -> Path:
    lines = ["# Business Insights & Recommendations", "",
             f"_Auto-generated {datetime.now():%Y-%m-%d %H:%M} | data source: **{source}**_", ""]
    if source == "synthetic":
        lines += ["> **Note:** numbers below come from the synthetic Olist-style dataset. Run the pipeline with the real "
                  "Olist CSVs (`python run_pipeline.py --real`) to regenerate this report with real findings.", ""]
    lines += ["## Headline KPIs", "", "| KPI | Value |", "|---|---|",
              f"| Delivered revenue | R${k['revenue']:,.0f} |", f"| Delivered orders | {k['orders']:,} |",
              f"| Unique customers | {k['customers']:,} |", f"| Average order value | R${k['aov']:,.2f} |",
              f"| Repeat customer rate | {k['repeat_pct']:.2f}% |", f"| Cancellation rate | {k['cancel_pct']:.2f}% |",
              f"| Late delivery rate | {k['late_pct']:.2f}% |", f"| Average review score | {k['review']:.2f} / 5 |", "",
              "## Business Recommendations", ""]
    order = {"High": 0, "Medium": 1, "Low": 2}
    for i, r in enumerate(sorted(recs, key=lambda x: order[x["priority"]]), 1):
        lines += [f"### {i}. {r['title']}  _(priority: {r['priority']} | {r['module']})_", "",
                  f"**What the data shows:** {r['insight']}", "", f"**Why it matters:** {r['why']}", "",
                  f"**Recommended action:** {r['action']}", ""]
    lines += ["## What this analysis cannot tell you", "",
              "- Profit and margin (no cost data), stock-out risk (no inventory data), conversion and cart abandonment (no web events).",
              "- Causality: patterns such as late delivery vs ratings are associations; confirm with experiments before large investments."]
    p = REPORTS / "business_insights.md"; p.write_text("\n".join(lines), encoding="utf-8"); return p


def write_weekly_summary(db: Database) -> Path:
    mx = pd.to_datetime(db.query("SELECT MAX(purchase_date) d FROM analytics.vw_delivered_orders").iloc[0, 0])
    cur0, prev0 = mx - pd.Timedelta(days=6), mx - pd.Timedelta(days=13)
    q = f"""SELECT CASE WHEN purchase_date >= DATE '{cur0:%Y-%m-%d}' THEN 'current' ELSE 'previous' END AS wk,
                   SUM(item_revenue) revenue, COUNT(*) orders, 100.0*AVG(is_late) late_pct, AVG(delivery_days) avg_days
            FROM analytics.vw_delivered_orders WHERE purchase_date >= DATE '{prev0:%Y-%m-%d}' GROUP BY 1"""
    w = db.query(q).set_index("wk")
    lines = [f"# Weekly Business Summary", "", f"_Week ending {mx:%Y-%m-%d} vs previous 7 days | generated {datetime.now():%Y-%m-%d}_", ""]
    if {"current", "previous"} <= set(w.index):
        c, p = w.loc["current"], w.loc["previous"]
        lines += ["| Metric | This week | Last week | Change |", "|---|---|---|---|",
                  f"| Revenue | R${c.revenue:,.0f} | R${p.revenue:,.0f} | {(c.revenue / p.revenue - 1) * 100:+.1f}% |",
                  f"| Orders | {int(c.orders):,} | {int(p.orders):,} | {(c.orders / p.orders - 1) * 100:+.1f}% |",
                  f"| Late-delivery % (among delivered) | {c.late_pct:.1f}% | {p.late_pct:.1f}% | {c.late_pct - p.late_pct:+.1f} pp |", ""]
    dec = run_named_query(db, "prd_declining_categories").head(3)
    lines += ["## Categories to watch (last 3 months vs previous 3)", ""]
    lines += [f"- **{r.category}**: {float(r.change_pct):+.1f}%" for r in dec.itertuples()]
    p = REPORTS / "weekly_summary.md"; p.write_text("\n".join(lines), encoding="utf-8"); return p


def write_pdf(db: Database, k: dict, fc: pd.DataFrame, rfm_summary: pd.DataFrame, source: str) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    pal = ["#7C5CFF", "#22D3EE", "#FFB547", "#34E5A1", "#FF5C8A"]
    path = REPORTS / "executive_report.pdf"
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=(11.7, 8.3)); fig.patch.set_facecolor("white")
        fig.text(0.06, 0.92, "E-Commerce Intelligence Report", fontsize=26, weight="bold", color="#161A35")
        fig.text(0.06, 0.88, f"Generated {datetime.now():%d %b %Y} | source: {source}", fontsize=11, color="#555")
        items = [("Revenue", f"R${k['revenue'] / 1e6:.2f}M"), ("Orders", f"{k['orders']:,}"), ("AOV", f"R${k['aov']:.0f}"),
                 ("Customers", f"{k['customers']:,}"), ("Repeat rate", f"{k['repeat_pct']:.1f}%"), ("Avg review", f"{k['review']:.2f}"),
                 ("Late deliveries", f"{k['late_pct']:.1f}%"), ("Cancellations", f"{k['cancel_pct']:.1f}%")]
        for i, (lab, val) in enumerate(items):
            x, y = 0.06 + (i % 4) * 0.23, 0.68 - (i // 4) * 0.2
            fig.patches.append(plt.Rectangle((x, y), 0.21, 0.16, transform=fig.transFigure, color=pal[i % 5], alpha=0.12))
            fig.text(x + 0.015, y + 0.085, val, fontsize=22, weight="bold", color="#161A35")
            fig.text(x + 0.015, y + 0.03, lab, fontsize=11, color="#444")
        pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(2, 1, figsize=(11.7, 8.3))
        a = fc[fc.kind == "actual"]; f = fc[fc.kind == "future"]; h = fc[fc.kind == "holdout"]
        ax[0].plot(a.month, a.actual / 1e3, color=pal[0], lw=2.5, label="Actual")
        ax[0].plot(h.month, h.forecast / 1e3, color=pal[2], ls="--", label="Hold-out forecast")
        ax[0].plot(f.month, f.forecast / 1e3, color=pal[3], lw=2.5, label=f"Forecast ({fc.model.iloc[0]})")
        ax[0].fill_between(f.month, f.lower / 1e3, f.upper / 1e3, color=pal[3], alpha=0.2)
        ax[0].set_title("Monthly revenue and forecast (R$ thousand)"); ax[0].legend(); ax[0].grid(alpha=0.25)
        cat = run_named_query(db, "rev_top_categories")
        ax[1].barh(cat.category[::-1], cat.revenue.astype(float)[::-1] / 1e3, color=pal[1]); ax[1].set_title("Top 10 categories by revenue (R$ thousand)")
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)

        fig, ax = plt.subplots(1, 2, figsize=(11.7, 8.3))
        ax[0].pie(rfm_summary.customers, labels=rfm_summary.segment, autopct="%1.0f%%", colors=pal * 2, textprops={"fontsize": 8})
        ax[0].set_title("Customers by RFM segment")
        d = run_named_query(db, "sat_delay_vs_rating")
        ax[1].bar(d.delivery_vs_estimate.str[3:], d.avg_review_score.astype(float), color=pal[4]); ax[1].set_ylim(0, 5)
        ax[1].set_title("Average review score by delivery vs estimate"); ax[1].tick_params(axis="x", rotation=25, labelsize=8)
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)
    return path

"""Turns analytical outputs into decision-ready business recommendations (insight -> why it matters -> action)."""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from python.database_loader import Database, run_named_query  # noqa: E402


def _r(db, name):
    return run_named_query(db, name)


def build_recommendations(db: Database, fc: pd.DataFrame | None = None, fc_metrics: pd.DataFrame | None = None,
                          churn: pd.DataFrame | None = None) -> list[dict]:
    recs: list[dict] = []

    def add(module, priority, title, insight, why, action):
        recs.append({"module": module, "priority": priority, "title": title, "insight": insight, "why": why, "action": action})

    # 1. revenue trajectory ------------------------------------------------------------
    m = _r(db, "rev_monthly_trend"); m["revenue"] = m["revenue"].astype(float)
    if len(m) >= 12:
        first6, last6 = m.revenue.iloc[:6].mean(), m.revenue.iloc[-6:].mean()
        peak = m.loc[m.revenue.idxmax()]
        add("Executive", "High", "Revenue is scaling, with a single seasonal spike",
            f"Average monthly revenue grew from R${first6:,.0f} (first 6 months) to R${last6:,.0f} (latest 6 months), "
            f"{(last6 / first6 - 1) * 100:+.0f}%. The peak month was {pd.to_datetime(peak.month):%b %Y} at R${peak.revenue:,.0f}.",
            "A one-month spike inflates averages and can hide whether the underlying trend is healthy.",
            "Plan inventory, seller capacity and logistics for the peak period at least 8 weeks ahead, and judge growth on rolling 3-month averages rather than single months.")
    # 2. category concentration --------------------------------------------------------
    cat = _r(db, "rev_category_pareto"); top3 = cat.head(3)
    add("Product", "Medium", "Revenue concentrated in a few categories",
        f"The top 3 categories ({', '.join(top3.category)}) contribute {top3.share_pct.astype(float).sum():.1f}% of revenue.",
        "High concentration raises exposure to demand shocks and seller issues in a few categories.",
        "Protect the top categories (availability, delivery SLAs) while testing targeted growth in mid-sized categories with rising trend.")
    # 3. declining categories ----------------------------------------------------------
    dec = _r(db, "prd_declining_categories"); dec["change_pct"] = dec.change_pct.astype(float)
    dec = dec[(dec.change_pct < -10) & (dec.previous_3m_revenue.astype(float) > 3000)].head(3)
    if len(dec):
        names = ", ".join(f"{r.category} ({r.change_pct:+.0f}%)" for r in dec.itertuples())
        add("Product", "High", "Categories losing momentum",
            f"Revenue over the last 3 full months versus the prior 3 months fell in: {names}.",
            "Falling categories may signal pricing, availability or demand problems, but the data alone cannot say which.",
            "Investigate pricing versus competitors, stock availability and review scores before spending more on promotion. Re-test after one quarter.")
    # 4. retention ---------------------------------------------------------------------
    rep = _r(db, "cus_repeat_rate").iloc[0]; gap = _r(db, "cus_days_to_second_order").iloc[0]
    add("Customer", "High", "Very few customers come back",
        f"Only {float(rep.repeat_customer_pct):.1f}% of {int(rep.total_customers):,} customers placed a second order; "
        f"those who did returned after {float(gap.avg_days_to_second_order):.0f} days on average.",
        "Acquisition-only growth is expensive. Even small gains in repeat rate compound across a large customer base.",
        "Launch a post-purchase journey that offers a second-order incentive around day 20-30 and target categories with natural repurchase (health & beauty, pet, perfumery).")
    # 5. delivery -> ratings -----------------------------------------------------------
    d = _r(db, "sat_delay_vs_rating"); d["avg_review_score"] = d.avg_review_score.astype(float)
    d["orders"] = d.orders.astype(int)
    ok = d.iloc[0:3]; best = float((ok.avg_review_score * ok.orders).sum() / ok.orders.sum()); worst = d.iloc[-1].avg_review_score
    perf = _r(db, "del_monthly_performance"); perf["orders"] = perf.delivered_orders.astype(int)
    late = float((perf.late_pct.astype(float) * perf.orders).sum() / perf.orders.sum())
    add("Operations", "High", "Late delivery is strongly linked to bad reviews",
        f"Orders that arrive on time or early average {best:.2f} stars versus {worst:.2f} when 6+ days late. Overall late-delivery rate is about {late:.1f}%.",
        "Delivery delay is strongly associated with low ratings, so fixing logistics is likely the fastest lever for better reviews (confirm with an A/B test on delivery estimates).",
        "Set seller SLAs and padding on delivery estimates in slow regions, and escalate sellers who breach them repeatedly.")
    # 6. sellers -----------------------------------------------------------------------
    sel = _r(db, "del_seller_late_ranking"); sel["late_pct"] = sel.late_pct.astype(float)
    if len(sel):
        add("Operations", "Medium", "A small group of sellers delivers late far more often",
            f"The worst 5 sellers (30+ orders) are late on {sel.late_pct.head(5).mean():.0f}% of orders versus a platform average of about {late:.0f}%.",
            "A few poor performers damage the brand for every customer who buys from them.",
            "Place high-late-rate sellers on a performance plan, reduce their search ranking until they recover, and share seller scorecards monthly.")
    # 7. regional gap ------------------------------------------------------------------
    reg = _r(db, "del_by_region"); reg["avg_delivery_days"] = reg.avg_delivery_days.astype(float)
    slow, fast = reg.iloc[0], reg.iloc[-1]
    add("Operations", "Medium", "Large delivery-time gap between regions",
        f"{slow.region} averages {slow.avg_delivery_days:.1f} days to deliver versus {fast.avg_delivery_days:.1f} days in {fast.region}.",
        "Slow regions suffer worse customer experience and higher freight cost, which can suppress demand there.",
        "Evaluate regional fulfilment hubs or carrier changes for the slowest region, and investigate whether low sales there come from demand or delivery friction.")
    # 8. cancellations -----------------------------------------------------------------
    can = _r(db, "rev_cancellation_impact")
    lost = can.lost_revenue.astype(float).sum(); tot = can.delivered_revenue.astype(float).sum()
    add("Executive", "Medium", "Cancellations quietly leak revenue",
        f"Cancelled and unavailable orders represent R${lost:,.0f} of item value, about {lost / (lost + tot) * 100:.1f}% of potential revenue.",
        "Unavailable items point to stock-sync problems between sellers and the marketplace.",
        "Require sellers to confirm stock at checkout and penalise repeated 'unavailable' cancellations.")
    # 9. payments ----------------------------------------------------------------------
    pay = _r(db, "pay_by_method"); cc = pay[pay.payment_type == "credit_card"]
    if len(cc):
        add("Revenue", "Low", "Credit cards and instalments dominate payments",
            f"Credit cards account for {float(cc.share_pct.iloc[0]):.1f}% of payment value; boleto is the main alternative.",
            "Instalments let customers afford larger baskets, but boleto customers abandon more often in many marketplaces (not measurable here).",
            "Keep instalment options visible on higher-priced items, and test boleto reminders to reduce unpaid orders.")
    # 10. forecast ---------------------------------------------------------------------
    if fc is not None and fc_metrics is not None:
        fut = fc[fc.kind == "future"].head(3); best_m = fc_metrics.iloc[0]
        add("Predictive", "Medium", "Short-term revenue outlook",
            f"The best model on hold-out data ({best_m.model}, MAPE {best_m.MAPE:.1f}%) projects R${fut.forecast.sum():,.0f} over the next 3 months.",
            "The forecast gives a planning baseline but does not capture holidays or promotions if history is short.",
            "Use it as the base case for capacity planning and add judgement for known campaigns; refresh monthly and monitor forecast error.")
    # 11. churn ------------------------------------------------------------------------
    if churn is not None:
        hv = churn[churn.risk_segment == "High-value at risk"]
        add("Customer", "High", "High-value customers are drifting away",
            f"{len(hv):,} high-spending customers are 60-180 days past their last order, holding R${hv.monetary.sum():,.0f} in historical spend.",
            "These customers are cheaper to win back than new customers are to acquire.",
            "Send personalised win-back offers before day 180 and measure the response against a holdout group.")
    return recs

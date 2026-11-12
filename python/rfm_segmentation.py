"""RFM segmentation.

R score : 5 = most recent (quintiles of recency days).
F score : marketplace data has ~97% one-time buyers, so quintiles would split ties arbitrarily.
          We therefore use business bins:  1 order -> 1,  2 orders -> 3,  3+ orders -> 5.
M score : quintiles of lifetime item revenue (5 = highest spend).
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SEGMENT_ACTIONS = {
    "Champions": "Reward & upsell: early access, loyalty tier, referral programme",
    "Loyal Customers": "Keep engaged: bundles, subscribe-and-save, review requests",
    "Potential Loyalists": "Convert to 2nd/3rd order: personalised cross-sell within 30 days",
    "New Customers": "Onboard: welcome journey, second-purchase coupon",
    "Need Attention": "Nudge: reminder + category recommendations before they lapse",
    "At Risk": "Win back: high-value lapsed - personalised offer, concierge outreach",
    "Hibernating": "Low-cost reactivation only (email); do not over-invest",
}


def _quintile(series: pd.Series, reverse: bool = False) -> pd.Series:
    ranked = series.rank(method="first", ascending=not reverse)
    return pd.qcut(ranked, 5, labels=[1, 2, 3, 4, 5]).astype(int)


def rfm_segment(feat: pd.DataFrame) -> pd.DataFrame:
    d = feat[["customer_unique_id", "customer_state", "recency_days", "frequency", "monetary"]].copy()
    d["r_score"] = _quintile(d["recency_days"], reverse=True)          # smaller recency -> higher score
    d["f_score"] = np.select([d.frequency >= 3, d.frequency == 2], [5, 3], default=1)
    d["m_score"] = _quintile(d["monetary"])
    r, f, m = d.r_score, d.f_score, d.m_score
    d["segment"] = np.select(
        [(r >= 4) & (f >= 3),
         (r <= 2) & ((f >= 3) | (m >= 4)),
         (f >= 3),
         (r >= 4) & (f == 1) & (m >= 3),
         (r >= 4) & (f == 1),
         (r <= 2),
         ],
        ["Champions", "At Risk", "Loyal Customers", "Potential Loyalists", "New Customers", "Hibernating"],
        default="Need Attention")
    d["rfm_code"] = d.r_score.astype(str) + d.f_score.astype(str) + d.m_score.astype(str)
    d["recommended_action"] = d["segment"].map(SEGMENT_ACTIONS)
    return d


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    s = rfm.groupby("segment").agg(customers=("customer_unique_id", "count"), revenue=("monetary", "sum"),
                                   avg_recency_days=("recency_days", "mean"), avg_orders=("frequency", "mean")).reset_index()
    s["customer_share_pct"] = 100 * s.customers / s.customers.sum()
    s["revenue_share_pct"] = 100 * s.revenue / s.revenue.sum()
    return s.sort_values("revenue", ascending=False)

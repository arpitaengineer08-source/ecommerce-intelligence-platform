"""Customer-level feature engineering: recency, frequency, monetary, AOV, simple CLV, behaviour flags."""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from python.database_loader import Database  # noqa: E402


def load_delivered_orders(db: Database) -> pd.DataFrame:
    return db.query("""SELECT order_id, customer_unique_id, customer_state, purchase_ts, purchase_date, purchase_month,
                              item_revenue, freight_value, is_late, avg_review_score, max_installments
                       FROM analytics.vw_delivered_orders""")


def customer_features(orders: pd.DataFrame, asof: pd.Timestamp | None = None) -> pd.DataFrame:
    """One row per customer using only orders placed BEFORE `asof` (prevents label leakage)."""
    o = orders.copy()
    o["purchase_ts"] = pd.to_datetime(o["purchase_ts"])
    asof = pd.Timestamp(asof) if asof is not None else o["purchase_ts"].max().normalize() + pd.Timedelta(days=1)
    o = o[o["purchase_ts"] < asof]
    g = o.groupby("customer_unique_id")
    f = g.agg(customer_state=("customer_state", "first"), frequency=("order_id", "nunique"),
              monetary=("item_revenue", "sum"), first_order=("purchase_ts", "min"), last_order=("purchase_ts", "max"),
              avg_review=("avg_review_score", "mean"), late_share=("is_late", "mean"),
              avg_installments=("max_installments", "mean")).reset_index()
    f["recency_days"] = (asof - f["last_order"]).dt.days
    f["tenure_days"] = (asof - f["first_order"]).dt.days
    f["avg_order_value"] = f["monetary"] / f["frequency"]
    f["avg_review"] = f["avg_review"].fillna(f["avg_review"].mean())
    f["late_share"] = f["late_share"].fillna(0)
    f["avg_installments"] = f["avg_installments"].fillna(1)
    return f


def portfolio_clv(feat: pd.DataFrame) -> dict:
    """Simple, transparent portfolio-level CLV = AOV x orders per customer. (Historical, not predictive.)"""
    aov = feat["monetary"].sum() / feat["frequency"].sum()
    opc = feat["frequency"].mean()
    return {"aov": float(aov), "orders_per_customer": float(opc), "historical_clv": float(aov * opc),
            "repeat_rate_pct": float((feat["frequency"] > 1).mean() * 100)}

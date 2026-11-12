"""Churn-risk identification.

DEFINITION (inactivity based): a customer is 'lapsed' when 180+ days passed since the last purchase.
PREDICTION TARGET (for the optional logistic regression): among customers who bought before a cutoff
date, will they purchase again in the following 120 days?  Features use ONLY pre-cutoff data (no leakage)
and the model is evaluated on a stratified hold-out set with ROC-AUC.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from python.feature_engineering import customer_features  # noqa: E402

FEATURES = ["recency_days", "frequency", "monetary", "avg_order_value", "avg_review", "late_share", "avg_installments", "tenure_days"]
WINDOW_DAYS = 120


def train_repurchase_model(orders: pd.DataFrame):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, average_precision_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    o = orders.copy(); o["purchase_ts"] = pd.to_datetime(o["purchase_ts"])
    end = o.purchase_ts.max()
    cutoff = end - pd.Timedelta(days=WINDOW_DAYS)
    feats = customer_features(o, asof=cutoff)
    later = set(o[(o.purchase_ts >= cutoff)]["customer_unique_id"])
    feats["target"] = feats["customer_unique_id"].isin(later).astype(int)
    X, y = feats[FEATURES], feats["target"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
    model = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=500))
    model.fit(Xtr, ytr)
    p = model.predict_proba(Xte)[:, 1]
    metrics = {"customers_in_sample": int(len(feats)), "positive_rate_pct": float(y.mean() * 100),
               "roc_auc": float(roc_auc_score(yte, p)), "avg_precision": float(average_precision_score(yte, p)),
               "baseline_precision": float(yte.mean()), "cutoff": str(cutoff.date()), "window_days": WINDOW_DAYS}
    coefs = pd.DataFrame({"feature": FEATURES, "coefficient": model[-1].coef_[0]}).sort_values("coefficient", key=abs, ascending=False)
    return model, metrics, coefs


def score_customers(orders: pd.DataFrame, model) -> pd.DataFrame:
    feat = customer_features(orders)
    feat["repurchase_prob"] = model.predict_proba(feat[FEATURES])[:, 1]
    feat["expected_value_next_window"] = feat["repurchase_prob"] * feat["avg_order_value"]
    r = feat["recency_days"]
    feat["inactivity_status"] = np.select([r <= 60, r <= 120, r <= 180], ["Active", "Cooling", "At risk"], default="Lapsed")
    high_value = feat["monetary"] >= feat["monetary"].quantile(0.8)
    feat["risk_segment"] = np.select(
        [(feat.inactivity_status.isin(["Cooling", "At risk"])) & high_value,
         feat.inactivity_status.isin(["Cooling", "At risk"]),
         feat.inactivity_status == "Lapsed"],
        ["High-value at risk", "Standard at risk", "Lapsed"], default="Healthy")
    feat["retention_action"] = feat["risk_segment"].map({
        "High-value at risk": "Priority win-back: personal offer + free shipping before day 180",
        "Standard at risk": "Automated email/WhatsApp reminder with category recommendations",
        "Lapsed": "Low-cost reactivation campaign; suppress after 2 attempts",
        "Healthy": "No action - keep engaged with normal communications"})
    return feat[["customer_unique_id", "customer_state", "recency_days", "frequency", "monetary", "avg_order_value",
                 "repurchase_prob", "expected_value_next_window", "inactivity_status", "risk_segment", "retention_action"]]

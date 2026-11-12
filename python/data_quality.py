"""Automated data-quality monitoring: key checks, referential integrity, business-rule checks,
payment reconciliation and snapshot-based drift detection. Produces reports/data_quality_report.md."""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA_PROCESSED, REPORTS  # noqa: E402

SNAPSHOT = DATA_PROCESSED / "quality_snapshot.json"


def run_checks(clean: dict[str, pd.DataFrame]) -> pd.DataFrame:
    c, o, i, p, r, pr, s = (clean[k] for k in ["customers", "orders", "order_items", "payments", "reviews", "products", "sellers"])
    checks = []

    def add(name, table, passed, detail, severity="error"):
        checks.append({"check": name, "table": table, "status": "PASS" if passed else ("FAIL" if severity == "error" else "WARN"), "detail": detail})

    # primary keys
    for tbl, df, keys in [("customers", c, ["customer_id"]), ("orders", o, ["order_id"]), ("order_items", i, ["order_id", "order_item_id"]),
                          ("payments", p, ["order_id", "payment_sequential"]), ("products", pr, ["product_id"]), ("sellers", s, ["seller_id"]),
                          ("reviews", r, ["review_id", "order_id"])]:
        d = int(df.duplicated(keys).sum())
        add(f"Primary key unique ({'+'.join(keys)})", tbl, d == 0, f"{d} duplicate keys")
    # foreign keys
    for name, child, col, parent, pcol in [("orders.customer_id -> customers", o, "customer_id", c, "customer_id"),
                                           ("order_items.order_id -> orders", i, "order_id", o, "order_id"),
                                           ("order_items.product_id -> products", i, "product_id", pr, "product_id"),
                                           ("order_items.seller_id -> sellers", i, "seller_id", s, "seller_id"),
                                           ("payments.order_id -> orders", p, "order_id", o, "order_id"),
                                           ("reviews.order_id -> orders", r, "order_id", o, "order_id")]:
        bad = int((~child[col].isin(parent[pcol])).sum())
        add(f"Foreign key: {name}", name.split(".")[0], bad == 0, f"{bad} orphan rows")
    # nulls
    for tbl, df, col in [("orders", o, "order_purchase_timestamp"), ("order_items", i, "price"), ("customers", c, "customer_unique_id")]:
        n = int(df[col].isna().sum()); add(f"No nulls in {col}", tbl, n == 0, f"{n} nulls")
    n = int((pr["product_category_name"] == "unknown").sum())
    add("Products with known category", "products", n / len(pr) < 0.05, f"{n} unknown ({n/len(pr):.1%})", "warn")
    # business rules
    d = o[o.order_status == "delivered"]
    n = int((d.order_delivered_customer_date.isna()).sum())
    add("Delivered orders have delivery date", "orders", n == 0, f"{n} missing", "warn")
    n = int((o.order_delivered_carrier_date < o.order_purchase_timestamp).sum())
    add("Carrier pickup not before purchase", "orders", n == 0, f"{n} violations", "warn")
    add("Review score within 1-5", "reviews", bool(r.review_score.between(1, 5).all()), "range check")
    add("Prices strictly positive", "order_items", bool((i.price > 0).all()), f"{int((i.price <= 0).sum())} non-positive", "warn")
    # reconciliation: payments ~= items + freight
    tot = i.groupby("order_id").agg(v=("price", "sum"), f=("freight_value", "sum")); tot["items_total"] = tot.v + tot.f
    pay = p.groupby("order_id")["payment_value"].sum()
    j = tot.join(pay, how="inner"); diff = ((j.items_total - j.payment_value).abs() > 1.0).mean()
    add("Payments reconcile with items + freight (+-R$1)", "payments", diff < 0.02, f"{diff:.2%} of orders mismatch", "warn")
    # drift vs previous snapshot
    snap = {k: int(len(v)) for k, v in clean.items()}
    if SNAPSHOT.exists():
        prev = json.loads(SNAPSHOT.read_text())
        for k, n_now in snap.items():
            n_prev = prev.get(k)
            if n_prev:
                chg = (n_now - n_prev) / n_prev
                add(f"Row-count drift vs last run (<20%)", k, abs(chg) < 0.20, f"{n_prev:,} -> {n_now:,} ({chg:+.1%})", "warn")
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(snap))
    return pd.DataFrame(checks)


def write_report(checks: pd.DataFrame, cleaning_log: list[dict], source: str) -> Path:
    REPORTS.mkdir(exist_ok=True)
    p = REPORTS / "data_quality_report.md"
    passed = (checks.status == "PASS").sum()
    lines = [f"# Data Quality Report", "", f"_Generated {datetime.now():%Y-%m-%d %H:%M} | data source: **{source}**_", "",
             f"**{passed}/{len(checks)} checks passed** | "
             f"{(checks.status == 'WARN').sum()} warnings | {(checks.status == 'FAIL').sum()} failures", "",
             "## 1. Validation checks", "", "| Status | Check | Table | Detail |", "|---|---|---|---|"]
    icon = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}
    lines += [f"| {icon[r.status]} | {r.check} | {r.table} | {r.detail} |" for r in checks.itertuples()]
    lines += ["", "## 2. Cleaning actions applied", "", "| Table | Issue | Rows | Action |", "|---|---|---|---|"]
    lines += [f"| {x['table']} | {x['issue']} | {x['rows_affected']:,} | {x['action']} |" for x in cleaning_log if x["rows_affected"] > 0]
    lines += ["", "## 3. Known dataset limitations", "",
              "- No product cost data -> **profit/margin cannot be computed**; revenue and freight only.",
              "- No inventory snapshots -> **stock-out risk cannot be measured**.",
              "- No web sessions / cart events -> **conversion and cart abandonment are not available**.",
              "- `customer_id` is per-order; `customer_unique_id` is used to identify real customers."]
    if source == "synthetic":
        lines += ["- **Data source is synthetic** (Olist-schema generator). Replace with the real Olist CSVs for real insights."]
    p.write_text("\n".join(lines), encoding="utf-8")
    return p

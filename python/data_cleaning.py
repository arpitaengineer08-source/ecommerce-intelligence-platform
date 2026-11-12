"""Stage 2 - Cleaning: standardise types/categories, remove duplicates, repair or flag invalid records.
Every change is logged so the data-quality report can show exactly what was fixed."""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ORDER_TS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
            "order_delivered_customer_date", "order_estimated_delivery_date"]


def clean_all(raw: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    log: list[dict] = []

    def note(table, issue, n, action):
        log.append({"table": table, "issue": issue, "rows_affected": int(n), "action": action})

    # ---- customers
    c = raw["customers"].copy()
    n = c.duplicated("customer_id").sum(); c = c.drop_duplicates("customer_id"); note("customers", "duplicate customer_id", n, "dropped")
    c["customer_city"] = c["customer_city"].astype(str).str.strip().str.lower()
    c["customer_state"] = c["customer_state"].astype(str).str.strip().str.upper()

    # ---- orders
    o = raw["orders"].copy()
    n = o.duplicated("order_id").sum(); o = o.drop_duplicates("order_id"); note("orders", "duplicate order_id", n, "dropped")
    for col in ORDER_TS:
        before = o[col].notna().sum()
        o[col] = pd.to_datetime(o[col], errors="coerce")
        note("orders", f"unparseable {col}", before - o[col].notna().sum(), "set to NULL")
    o["order_status"] = o["order_status"].astype(str).str.strip().str.lower()
    bad = (o["order_delivered_customer_date"] < o["order_purchase_timestamp"])
    note("orders", "delivered before purchase (impossible)", bad.sum(), "delivery date set to NULL, order kept")
    o.loc[bad, "order_delivered_customer_date"] = pd.NaT
    inc = (o["order_status"] == "delivered") & o["order_delivered_customer_date"].isna()
    note("orders", "status=delivered but no delivery date", inc.sum(), "kept (excluded from delivery-time metrics)")
    o = o[o["customer_id"].isin(c["customer_id"])]

    # ---- items
    i = raw["order_items"].copy()
    n = i.duplicated(["order_id", "order_item_id"]).sum(); i = i.drop_duplicates(["order_id", "order_item_id"]); note("order_items", "duplicate (order_id, item_id)", n, "dropped")
    i["shipping_limit_date"] = pd.to_datetime(i["shipping_limit_date"], errors="coerce")
    n = ((i["price"] < 0) | (i["freight_value"] < 0)).sum(); i = i[(i["price"] >= 0) & (i["freight_value"] >= 0)]; note("order_items", "negative price/freight", n, "dropped")
    n = (~i["order_id"].isin(o["order_id"])).sum(); i = i[i["order_id"].isin(o["order_id"])]; note("order_items", "orphan order_id", n, "dropped")

    # ---- payments
    p = raw["payments"].copy()
    p["payment_type"] = p["payment_type"].astype(str).str.strip().str.lower()
    n = p.duplicated(["order_id", "payment_sequential"]).sum(); p = p.drop_duplicates(["order_id", "payment_sequential"]); note("payments", "duplicate (order_id, sequential)", n, "dropped")
    n = (~p["order_id"].isin(o["order_id"])).sum(); p = p[p["order_id"].isin(o["order_id"])]; note("payments", "orphan order_id", n, "dropped")
    p["payment_installments"] = p["payment_installments"].clip(lower=1)

    # ---- reviews
    r = raw["reviews"].copy()
    n = r.duplicated().sum(); r = r.drop_duplicates(); note("reviews", "fully duplicated rows", n, "dropped")
    n = r.duplicated(["review_id", "order_id"]).sum(); r = r.drop_duplicates(["review_id", "order_id"]); note("reviews", "duplicate (review_id, order_id)", n, "dropped")
    r["review_creation_date"] = pd.to_datetime(r["review_creation_date"], errors="coerce")
    r["review_answer_timestamp"] = pd.to_datetime(r["review_answer_timestamp"], errors="coerce")
    n = (~r["review_score"].between(1, 5)).sum(); r = r[r["review_score"].between(1, 5)]; note("reviews", "score outside 1-5", n, "dropped")
    r["review_comment_message"] = r["review_comment_message"].astype("string").str.strip()
    n = (~r["order_id"].isin(o["order_id"])).sum(); r = r[r["order_id"].isin(o["order_id"])]; note("reviews", "orphan order_id", n, "dropped")

    # ---- products
    pr = raw["products"].copy()
    n = pr.duplicated("product_id").sum(); pr = pr.drop_duplicates("product_id"); note("products", "duplicate product_id", n, "dropped")
    n = pr["product_category_name"].isna().sum()
    pr["product_category_name"] = pr["product_category_name"].fillna("unknown").str.strip().str.lower()
    note("products", "missing category", n, "filled with 'unknown'")
    pr["product_weight_g"] = pr["product_weight_g"].fillna(pr["product_weight_g"].median())

    # ---- sellers / geo / translation
    s = raw["sellers"].drop_duplicates("seller_id").copy()
    s["seller_city"] = s["seller_city"].astype(str).str.strip().str.lower()
    s["seller_state"] = s["seller_state"].astype(str).str.strip().str.upper()
    g = (raw["geolocation"].groupby("geolocation_zip_code_prefix")
         .agg(geolocation_lat=("geolocation_lat", "mean"), geolocation_lng=("geolocation_lng", "mean"),
              geolocation_state=("geolocation_state", "first")).reset_index())
    note("geolocation", "many rows per zip prefix", len(raw["geolocation"]) - len(g), "aggregated to 1 row per zip prefix")
    t = raw["category_translation"].drop_duplicates("product_category_name")

    clean = {"customers": c, "orders": o, "order_items": i, "payments": p, "reviews": r,
             "products": pr, "sellers": s, "geolocation": g, "category_translation": t}
    return clean, log

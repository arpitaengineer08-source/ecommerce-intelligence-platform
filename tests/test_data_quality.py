"""Data-quality tests: keys, referential integrity, business rules, reconciliation."""
import pandas as pd


def test_primary_keys_unique(raw_and_clean):
    _, c, _ = raw_and_clean
    assert not c["customers"].duplicated("customer_id").any()
    assert not c["orders"].duplicated("order_id").any()
    assert not c["order_items"].duplicated(["order_id", "order_item_id"]).any()
    assert not c["products"].duplicated("product_id").any()
    assert not c["reviews"].duplicated(["review_id", "order_id"]).any()


def test_foreign_keys_valid(raw_and_clean):
    _, c, _ = raw_and_clean
    assert c["order_items"]["order_id"].isin(c["orders"]["order_id"]).all()
    assert c["order_items"]["product_id"].isin(c["products"]["product_id"]).all()
    assert c["order_items"]["seller_id"].isin(c["sellers"]["seller_id"]).all()
    assert c["payments"]["order_id"].isin(c["orders"]["order_id"]).all()
    assert c["reviews"]["order_id"].isin(c["orders"]["order_id"]).all()
    assert c["orders"]["customer_id"].isin(c["customers"]["customer_id"]).all()


def test_business_rules(raw_and_clean):
    _, c, _ = raw_and_clean
    o = c["orders"]
    assert (c["order_items"]["price"] > 0).all()
    assert (c["order_items"]["freight_value"] >= 0).all()
    assert c["reviews"]["review_score"].between(1, 5).all()
    bad = o["order_delivered_customer_date"] < o["order_purchase_timestamp"]
    assert not bad.any(), "delivery before purchase must be cleaned"
    assert set(o["order_status"]) <= {"delivered", "shipped", "canceled", "unavailable", "invoiced", "processing", "created", "approved"}


def test_cleaning_removed_known_defects(raw_and_clean):
    raw, c, log = raw_and_clean
    assert len(c["reviews"]) <= len(raw["reviews"])
    assert (c["products"]["product_category_name"] != "").all()
    assert c["products"]["product_category_name"].notna().all()


def test_payments_reconcile_with_items(raw_and_clean):
    _, c, _ = raw_and_clean
    items = c["order_items"].assign(t=lambda d: d.price + d.freight_value).groupby("order_id")["t"].sum()
    pay = c["payments"].groupby("order_id")["payment_value"].sum()
    j = pd.concat([items, pay], axis=1, join="inner")
    assert ((j["t"] - j["payment_value"]).abs() > 1).mean() < 0.02

"""Builds the three-layer warehouse (raw -> staging -> analytics star schema) from DataFrames."""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import SQL_DIR, STATES  # noqa: E402
from python.database_loader import Database  # noqa: E402


def make_dim_date(start="2016-09-01", end="2019-06-30") -> pd.DataFrame:
    d = pd.DataFrame({"date_key": pd.date_range(start, end)})
    d["year"] = d.date_key.dt.year
    d["quarter"] = d.date_key.dt.quarter
    d["month"] = d.date_key.dt.month
    d["month_name"] = d.date_key.dt.strftime("%b")
    d["year_month"] = d.date_key.dt.strftime("%Y-%m")
    d["week_of_year"] = d.date_key.dt.isocalendar().week.astype(int)
    d["day_of_week"] = d.date_key.dt.dayofweek + 1
    d["day_name"] = d.date_key.dt.strftime("%a")
    d["is_weekend"] = (d.day_of_week >= 6).astype(int)
    d["date_key"] = d.date_key.dt.date
    return d


def make_dim_geography() -> pd.DataFrame:
    return pd.DataFrame([{"state": s, "region": r, "lat": la, "lon": lo} for s, (r, la, lo) in STATES.items()])


def build_warehouse(db: Database, raw: dict[str, pd.DataFrame], clean: dict[str, pd.DataFrame]) -> None:
    db.run_script(SQL_DIR / "schema.sql")
    for name, df in raw.items():
        db.load_df(df, name, "raw")
    for name, df in clean.items():
        db.load_df(df, name, "staging")
    db.load_df(make_dim_date(), "dim_date", "analytics")
    db.load_df(make_dim_geography(), "dim_geography", "analytics")
    db.run_script(SQL_DIR / "staging.sql")
    db.run_script(SQL_DIR / "views.sql")
    if db.is_postgres:
        db.run_script(SQL_DIR / "constraints_postgres.sql")

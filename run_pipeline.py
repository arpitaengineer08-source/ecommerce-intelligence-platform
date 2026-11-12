#!/usr/bin/env python
"""
End-to-end pipeline:  ingest -> clean -> validate -> warehouse (raw/staging/analytics) -> analytics -> exports -> reports

    python run_pipeline.py                 # synthetic Olist-style data (generated automatically)
    python run_pipeline.py --real          # use real Olist CSVs placed in data/raw/
    python run_pipeline.py --orders 50000  # bigger synthetic dataset
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402

from config import DATABASE_URL, DATA_PROCESSED, DUCKDB_PATH, POWERBI_EXPORT, REPORTS  # noqa: E402
from python import (cohort_analysis, data_ingestion, data_quality, feature_engineering, forecasting,  # noqa: E402
                    insights, report_generator, rfm_segmentation, scenario)
from python.churn import score_customers, train_repurchase_model  # noqa: E402
from python.data_cleaning import clean_all  # noqa: E402
from python.database_loader import Database, load_query_library  # noqa: E402
from python.warehouse import build_warehouse  # noqa: E402


def step(msg: str):
    print(f"\n\033[95m>>\033[0m {msg}", flush=True)
    return time.time()


def run(use_real=False, n_orders=22000, skip_reports=False, force_regenerate=False) -> dict:
    t0 = time.time()
    for d in (DATA_PROCESSED, POWERBI_EXPORT, REPORTS):
        d.mkdir(parents=True, exist_ok=True)

    (DATA_PROCESSED / "run_manifest.json").unlink(missing_ok=True)   # marks 'build in progress'
    t = step("1/7 Ingesting data")
    source = data_ingestion.ensure_data(use_real=use_real, n_orders=n_orders, force_regenerate=force_regenerate)
    raw = data_ingestion.load_raw()
    print(f"   source = {source}; " + ", ".join(f"{k}={len(v):,}" for k, v in list(raw.items())[:4]) + f"  ({time.time() - t:.1f}s)")

    t = step("2/7 Cleaning")
    clean, log = clean_all(raw)
    for x in log:
        if x["rows_affected"]:
            print(f"   - {x['table']}: {x['issue']} ({x['rows_affected']:,}) -> {x['action']}")

    t = step("3/7 Data-quality validation")
    checks = data_quality.run_checks(clean)
    data_quality.write_report(checks, log, source)
    print(f"   {int((checks.status == 'PASS').sum())}/{len(checks)} checks passed, {int((checks.status == 'FAIL').sum())} failures")

    t = step("4/7 Building warehouse (raw -> staging -> analytics star schema)")
    if not DATABASE_URL:
        DUCKDB_PATH.unlink(missing_ok=True)
    db = Database()
    build_warehouse(db, raw, clean)
    print(f"   engine = {'PostgreSQL' if db.is_postgres else 'DuckDB'}  ({time.time() - t:.1f}s)")

    t = step("5/7 Analytics: RFM, cohorts, churn, forecast, scenarios")
    orders = feature_engineering.load_delivered_orders(db)
    feat = feature_engineering.customer_features(orders)
    rfm = rfm_segmentation.rfm_segment(feat); rfm_sum = rfm_segmentation.segment_summary(rfm)
    cohort = cohort_analysis.cohort_table(db)
    model, cmet, ccoef = train_repurchase_model(orders)
    churn = score_customers(orders, model)
    series = forecasting.monthly_series(db)
    fmet, fcst = forecasting.run_forecast(series)
    base = scenario.baseline_from_db(db); scen = scenario.standard_scenarios(base)
    clv = feature_engineering.portfolio_clv(feat)
    outputs = {"rfm_segments": rfm.drop(columns=["recommended_action"]), "rfm_summary": rfm_sum, "cohort_retention": cohort,
               "revenue_forecast": fcst, "forecast_metrics": fmet, "churn_scores": churn, "churn_coefficients": ccoef,
               "churn_model_metrics": pd.DataFrame([cmet]), "scenarios": scen,
               "data_quality_checks": checks, "cleaning_log": pd.DataFrame(log)}
    for name, df in outputs.items():
        db.load_df(df, name, "analytics")
        df.to_csv(DATA_PROCESSED / f"{name}.csv", index=False)
    print(f"   RFM segments={rfm.segment.nunique()}  best forecast model={fmet.iloc[0].model} (MAPE {fmet.iloc[0].MAPE:.1f}%)  churn AUC={cmet['roc_auc']:.2f}")

    t = step("6/7 Exporting star schema for Power BI")
    for tbl in ["dim_customer", "dim_product", "dim_seller", "dim_date", "dim_geography", "fact_orders", "fact_order_items",
                "fact_payments", "fact_reviews", "rfm_segments", "cohort_retention", "revenue_forecast", "churn_scores"]:
        db.query(f"SELECT * FROM analytics.{tbl}").to_csv(POWERBI_EXPORT / f"{tbl}.csv", index=False)
    print(f"   CSVs written to {POWERBI_EXPORT.relative_to(Path(__file__).parent)}")

    recs = insights.build_recommendations(db, fcst, fmet, churn)
    pd.DataFrame(recs).to_csv(DATA_PROCESSED / "recommendations.csv", index=False)
    db.load_df(pd.DataFrame(recs), "recommendations", "analytics")
    k = report_generator.kpis(db)
    if not skip_reports:
        t = step("7/7 Generating reports")
        report_generator.write_business_insights(recs, k, source, fmet)
        report_generator.write_weekly_summary(db)
        report_generator.write_pdf(db, k, fcst, rfm_sum, source)
        cohort_analysis.plot_heatmap(cohort_analysis.retention_matrix(cohort), REPORTS / "cohort_retention_heatmap.png")
        print("   reports/: business_insights.md, weekly_summary.md, data_quality_report.md, executive_report.pdf, cohort heatmap")

    lib = load_query_library()
    manifest = {"generated_at": datetime.now().isoformat(timespec="seconds"), "source": source, "engine": "postgresql" if db.is_postgres else "duckdb",
                "orders": k["orders"], "sql_queries": int(len(lib)), "advanced_sql_queries": int((lib.level == "advanced").sum()),
                "clv": clv, "churn_model": cmet}
    (DATA_PROCESSED / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    db.close()
    print(f"\n\033[92mDONE\033[0m in {time.time() - t0:.1f}s  ->  streamlit run app/streamlit_app.py")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true", help="use real Olist CSVs in data/raw/")
    ap.add_argument("--orders", type=int, default=22000, help="synthetic order count")
    ap.add_argument("--regenerate", action="store_true", help="regenerate synthetic data")
    ap.add_argument("--skip-reports", action="store_true")
    a = ap.parse_args()
    run(use_real=a.real, n_orders=a.orders, skip_reports=a.skip_reports, force_regenerate=a.regenerate)
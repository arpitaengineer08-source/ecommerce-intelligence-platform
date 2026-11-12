# E-Commerce Intelligence Platform

An end-to-end analytics platform for an online marketplace. It answers one question:

> **What is happening in the business, why is it happening, and what should the company do next?**

Python ETL → SQL warehouse (raw / staging / star schema) → 43 documented SQL queries → RFM, cohorts, forecasting, churn risk,
scenarios → Streamlit dashboard + Power BI kit + automated reports.

![Executive overview](docs/screenshots/executive_overview.png)

## Quick start (VS Code)

```bash
# 1. open the folder in VS Code, then in the integrated terminal:
python -m venv .venv
.venv\Scripts\activate            # Windows      |   source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt

# 2. build everything (about 10 seconds)
python run_pipeline.py

# 3. launch the dashboard
streamlit run app/streamlit_app.py
```

The dashboard also builds the warehouse by itself on first launch if you skip step 2. Run the tests with `pytest`.
The `.vscode/launch.json` file gives you one-click Run/Debug entries for the pipeline, the app and the tests.

### Data: synthetic by default, real Olist in one command
No Kaggle login is needed to run the project: `python/generate_sample_data.py` creates a dataset with the **exact Olist file and column names**
(22,000 orders, realistic growth, Black Friday spike, regional delivery gaps, late-delivery → low-rating effect, plus deliberate data defects
for the cleaning step to catch).

To use the real data, put the 9 CSVs from [Kaggle Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) in `data/raw/` and run:

```bash
python run_pipeline.py --real
```

Every number in the reports and dashboard then comes from real orders, and nothing else changes. **Findings from synthetic data are
demonstrations, not real insights. Say so in your portfolio and re-run on the real dataset before quoting numbers.**

## What is inside

| Layer | What it does | Where |
|---|---|---|
| Ingestion & cleaning | Types, duplicates, invalid dates, orphan keys, category translation, full cleaning log | `python/data_ingestion.py`, `data_cleaning.py` |
| Data-quality monitoring | PK/FK checks, business rules, payment reconciliation, row-count drift vs previous run → report | `python/data_quality.py`, `reports/data_quality_report.md` |
| Warehouse | `raw` → `staging` → `analytics` star schema; four facts with separate grains, five dimensions, views | `sql/schema.sql`, `staging.sql`, `views.sql`, `python/warehouse.py` |
| SQL library | **43 queries (20 advanced)**: CTEs, window functions, LAG/LEAD, NTILE, RANK/DENSE_RANK, FILTER, percentiles | `sql/queries/*.sql` |
| Customer analytics | RFM segmentation, cohort retention, simple CLV, new vs returning | `rfm_segmentation.py`, `cohort_analysis.py`, `feature_engineering.py` |
| Forecasting | Moving average, seasonal naive, seasonal naive × YoY drift, Holt damped; MAE / RMSE / MAPE on a hold-out; intervals; limitations | `python/forecasting.py` |
| Churn risk | Inactivity-based definition, leak-free logistic regression (cutoff date, 120-day target), risk segments with actions | `python/churn.py` |
| Scenario analysis | AOV +5%, cancellations −2 pp, repeat +10% with stated assumptions | `python/scenario.py` |
| Insights & reports | Insight → why it matters → action; weekly summary; executive PDF | `insights.py`, `report_generator.py`, `reports/` |
| Dashboard | 10-page Streamlit app with global filters, SQL Lab, scenario simulator | `app/` |
| Power BI kit | Theme, 35+ DAX measures, Power Query M, relationships, page-by-page build guide | `powerbi/` |
| Notebooks | Six executed notebooks, one per analysis stage | `notebooks/` |
| Tests | 11 tests: keys, integrity, business rules, reconciliation, every SQL query runs, revenue not inflated by joins | `tests/` |

## Architecture

```
Olist CSVs ─► Python ETL ─► SQL warehouse ─► Analytics layer ─► Streamlit · Power BI · Reports
              ingest         raw                RFM · cohorts     decisions
              clean          staging            forecast · churn
              validate       analytics (star)   scenarios
```

**Star schema:** `fact_orders` (1 row / order), `fact_order_items` (/ item), `fact_payments` (/ payment), `fact_reviews` (/ review),
and `dim_customer`, `dim_product`, `dim_seller`, `dim_date`, `dim_geography`. The facts are kept at separate grains because joining payments, reviews
and items directly multiplies rows and inflates revenue. `tests/test_sql_and_analytics.py` proves item revenue equals order revenue.

## Database engine
- **Default: DuckDB** (a file at `data/ecommerce.duckdb`, nothing to install). Its SQL dialect is PostgreSQL-compatible.
- **PostgreSQL:** set `DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/ecommerce` and run the pipeline. The same SQL files build the
  schemas, and `sql/constraints_postgres.sql` adds primary keys and indexes. *The test suite was run against DuckDB; the PostgreSQL path uses
  standard SQL (`ROUND(CAST(... AS NUMERIC), 2)`, `FILTER`, `DATE_TRUNC`) but verify it on your server.*

## Honest limitations (put these in your interview answers)
- Olist has **no product cost, inventory, web session or cart data**, so profit, stock-out risk and cart abandonment are deliberately *not* computed.
- Customers: 97% buy once, so RFM frequency uses business bins (1 / 2 / 3+ orders) instead of quintiles, which would split ties arbitrarily.
- Forecast history is about 20 months: annual seasonality is learned from a single cycle. The app shows model error against baselines and the limitations.
- The churn model is weak on this data (ROC-AUC ≈ 0.54 on synthetic data) and the app says so; the rule-based risk segments drive the actions.
- Late delivery vs rating is an **association**; confirm causality with an experiment before large investments.
- A `.pbix` file cannot be generated outside Power BI Desktop. `powerbi/` contains everything to build it in about 90 minutes.

## How to talk about this project
- *"I built a layered warehouse with a star schema and tested that joins don't inflate revenue."*
- *"Forecasts are judged against naive baselines on a hold-out, with MAE/RMSE/MAPE and stated limitations."*
- *"Every chart maps to a business question and a recommended action."* (see `reports/business_insights.md`)
- *"I separated 'what the data shows' from 'what it cannot show' (profit, inventory, cart abandonment)."*

## Repository layout
```
app/            Streamlit front-end (streamlit_app.py, style.py)
data/           raw/ (git-ignored), processed/ (outputs, powerbi/ CSVs)
docs/           screenshots
notebooks/      01 exploration … 06 forecasting (executed)
powerbi/        theme.json, DAX_measures.md, power_query_import.m, DASHBOARD_BUILD_GUIDE.md
python/         ETL, analytics, reporting modules
reports/        business_insights.md, weekly_summary.md, data_quality_report.md, executive_report.pdf, cohort heatmap
sql/            schema.sql, staging.sql, views.sql, constraints_postgres.sql, queries/ (43 analytical queries)
tests/          pytest suite
run_pipeline.py One-command pipeline (flags: --real, --orders N, --regenerate, --skip-reports)
```

## Extending it
Add queries to `sql/queries/*.sql` using the `-- name / -- title / -- question / -- level` header; they appear in the SQL Lab automatically.

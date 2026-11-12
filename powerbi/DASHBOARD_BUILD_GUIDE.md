# Power BI build guide (about 90 minutes)

A `.pbix` file is a binary that can only be authored in Power BI Desktop, so this folder gives you everything needed to
build it quickly and consistently with the Streamlit app: data, DAX, Power Query, theme and page layouts.

## Steps
1. Run the pipeline: `python run_pipeline.py` (creates `data/processed/powerbi/*.csv`).
2. Power BI Desktop > **View > Themes > Browse for themes** > `powerbi/theme.json` (midnight + aurora palette).
3. Import the CSVs using `power_query_import.m` (parameter `DataFolder`).
4. Mark `Dim_Date` as date table and create the relationships listed in `DAX_measures.md`.
5. Create the measures from `DAX_measures.md` in a `_Measures` table.
6. Build the five pages below. Save as `powerbi/ecommerce_dashboard.pbix`, export screenshots to `powerbi/dashboard_screenshots/`.
7. Optional: connect to PostgreSQL instead of CSVs (Get data > PostgreSQL, schema `analytics`).

## Slicers (sync across pages: View > Sync slicers)
Date (Dim_Date[date_key], between), Product category (Dim_Product[category]), Customer state (Dim_Geography[state]),
Seller (Dim_Seller[seller_id]), Order status (Fact_Orders[order_status]).

## Pages
| Page | KPI cards | Visuals | Business question |
|---|---|---|---|
| 1. Executive Overview | Total Revenue, Delivered Orders, AOV, Total Customers, Repeat Customer Rate %, MoM Growth % | Revenue + orders combo by month, category treemap, filled/bubble map by state, order-status donut | Is the business healthy? |
| 2. Customer Intelligence | New Customers, Repeat Customers, Customer Lifetime Revenue, Avg Purchase Frequency | RFM segment bar (RFM_Segments[segment]), cohort matrix (cohort_retention: rows cohort_month, columns month_index, value retention_pct, conditional formatting), top customers table, state bars | Who should we keep? |
| 3. Product Performance | Units Sold, Total Revenue, Average Selling Price, Revenue by Category % | Top/Bottom N products (Top N filter), category bars, Pareto (line + column), monthly trend by category | What sells and what does not? |
| 4. Operations & Delivery | Avg Delivery Days, Late Delivery %, Cancellation Rate %, Avg Freight per Order | Estimated vs actual by state (clustered column), seller scatter (late % vs orders), delay trend line, order-status trend | Do we keep our promise? |
| 5. Customer Satisfaction | Avg Review Score, Low Rating %, Review Count | Rating distribution, review trend, low-rated categories, delivery-delay bucket vs rating | Why are customers unhappy? |

Optional page 6: **Forecast and Risk** using `revenue_forecast` (line chart with `kind` as legend) and `churn_scores` (risk_segment donut).

## Design rules that make it look professional
- 1920x1080 canvas, 12-16 px gutters, KPI row on top, one primary visual per page that takes ~40% of the area.
- Titles state the question or finding ("Late deliveries cost 2 review stars"), not the chart type.
- Use conditional formatting colors only for good/neutral/bad meaning (theme: mint/amber/rose).
- Add tooltips pages for category and state drill-downs, and bookmarks for a "Story" navigation bar.

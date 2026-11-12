-- =====================================================================================
-- MODULE 1 / 5 : REVENUE ANALYSIS      (revenue = item price of DELIVERED orders)
-- Format per query: name | title | question | level   -> parsed by python/database_loader.py
-- =====================================================================================

-- name: rev_monthly_trend
-- title: Monthly revenue, orders and AOV
-- question: How is the business growing month over month?
-- level: basic
SELECT purchase_month AS month,
       ROUND(CAST(SUM(item_revenue) AS NUMERIC), 2)                     AS revenue,
       COUNT(*)                                                         AS orders,
       ROUND(CAST(SUM(item_revenue) / COUNT(*) AS NUMERIC), 2)          AS avg_order_value
FROM analytics.vw_delivered_orders
GROUP BY purchase_month
ORDER BY purchase_month;

-- name: rev_top_categories
-- title: Top 10 revenue-generating categories
-- question: Which categories carry the business?
-- level: basic
SELECT category,
       ROUND(CAST(SUM(price) AS NUMERIC), 2) AS revenue,
       COUNT(*)                              AS units_sold,
       ROUND(CAST(AVG(price) AS NUMERIC), 2) AS avg_selling_price
FROM analytics.vw_delivered_items
GROUP BY category
ORDER BY revenue DESC
LIMIT 10;

-- name: rev_mom_growth
-- title: Month-over-month revenue growth (LAG)
-- question: Which months accelerated or slowed?
-- level: advanced
WITH m AS (
    SELECT purchase_month AS month, SUM(item_revenue) AS revenue
    FROM analytics.vw_delivered_orders GROUP BY purchase_month
)
SELECT month,
       ROUND(CAST(revenue AS NUMERIC), 2)                                             AS revenue,
       ROUND(CAST(LAG(revenue) OVER (ORDER BY month) AS NUMERIC), 2)                  AS prev_month_revenue,
       ROUND(CAST(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / NULLIF(LAG(revenue) OVER (ORDER BY month), 0) AS NUMERIC), 1)          AS mom_growth_pct
FROM m
ORDER BY month;

-- name: rev_category_pareto
-- title: Category revenue share and cumulative share (Pareto)
-- question: How concentrated is revenue in a few categories?
-- level: advanced
WITH c AS (
    SELECT category, SUM(price) AS revenue FROM analytics.vw_delivered_items GROUP BY category
)
SELECT category,
       ROUND(CAST(revenue AS NUMERIC), 2) AS revenue,
       ROUND(CAST(100.0 * revenue / SUM(revenue) OVER () AS NUMERIC), 2) AS share_pct,
       ROUND(CAST(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER () AS NUMERIC), 2) AS cumulative_share_pct
FROM c
ORDER BY revenue DESC;

-- name: rev_by_region_state
-- title: Revenue by region and state
-- question: Which regions generate the most revenue and which underperform?
-- level: basic
SELECT g.region, fo.customer_state AS state,
       ROUND(CAST(SUM(fo.item_revenue) AS NUMERIC), 2) AS revenue,
       COUNT(*)                                       AS orders,
       COUNT(DISTINCT fo.customer_unique_id)          AS customers
FROM analytics.vw_delivered_orders fo
JOIN analytics.dim_geography g ON g.state = fo.customer_state
GROUP BY g.region, fo.customer_state
ORDER BY revenue DESC;

-- name: rev_yoy_comparison
-- title: Year-over-year growth, same months (Jan-Aug)
-- question: Are we bigger than the same period last year?
-- level: advanced
SELECT EXTRACT(MONTH FROM purchase_month) AS month_no,
       ROUND(CAST(SUM(item_revenue) FILTER (WHERE EXTRACT(YEAR FROM purchase_month) = 2017) AS NUMERIC), 2) AS revenue_2017,
       ROUND(CAST(SUM(item_revenue) FILTER (WHERE EXTRACT(YEAR FROM purchase_month) = 2018) AS NUMERIC), 2) AS revenue_2018,
       ROUND(CAST(100.0 * (SUM(item_revenue) FILTER (WHERE EXTRACT(YEAR FROM purchase_month) = 2018)
             / NULLIF(SUM(item_revenue) FILTER (WHERE EXTRACT(YEAR FROM purchase_month) = 2017), 0) - 1) AS NUMERIC), 1) AS yoy_growth_pct
FROM analytics.vw_delivered_orders
WHERE EXTRACT(MONTH FROM purchase_month) <= 8
GROUP BY 1
ORDER BY 1;

-- name: rev_day_of_week
-- title: Revenue by day of week
-- question: When should promotions and staffing be scheduled?
-- level: basic
SELECT EXTRACT(DOW FROM purchase_date) AS dow_no,
       CASE EXTRACT(DOW FROM purchase_date) WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue' WHEN 3 THEN 'Wed'
            WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri' ELSE 'Sat' END AS day_name,
       COUNT(*) AS orders,
       ROUND(CAST(SUM(item_revenue) AS NUMERIC), 2) AS revenue
FROM analytics.vw_delivered_orders
GROUP BY 1, 2
ORDER BY 1;

-- name: rev_rolling_3m
-- title: Rolling 3-month average and running total revenue
-- question: What is the underlying trend once monthly noise is removed?
-- level: advanced
WITH m AS (
    SELECT purchase_month AS month, SUM(item_revenue) AS revenue FROM analytics.vw_delivered_orders GROUP BY 1
)
SELECT month,
       ROUND(CAST(revenue AS NUMERIC), 2) AS revenue,
       ROUND(CAST(AVG(revenue) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS NUMERIC), 2) AS rolling_3m_avg,
       ROUND(CAST(SUM(revenue) OVER (ORDER BY month) AS NUMERIC), 2) AS cumulative_revenue
FROM m
ORDER BY month;

-- name: rev_order_status_mix
-- title: Order status distribution
-- question: What share of orders never reach the customer?
-- level: basic
SELECT order_status,
       COUNT(*) AS orders,
       ROUND(CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC), 2) AS share_pct
FROM analytics.fact_orders
GROUP BY order_status
ORDER BY orders DESC;

-- name: rev_cancellation_impact
-- title: Revenue lost to cancelled / unavailable orders by month
-- question: How much revenue leaks through cancellations?
-- level: basic
SELECT purchase_month AS month,
       ROUND(CAST(SUM(item_revenue) FILTER (WHERE order_status = 'delivered') AS NUMERIC), 2)                       AS delivered_revenue,
       ROUND(CAST(SUM(item_revenue) FILTER (WHERE order_status IN ('canceled', 'unavailable')) AS NUMERIC), 2)     AS lost_revenue,
       ROUND(CAST(100.0 * COUNT(*) FILTER (WHERE order_status IN ('canceled', 'unavailable')) / COUNT(*) AS NUMERIC), 2) AS cancel_rate_pct
FROM analytics.fact_orders
GROUP BY purchase_month
ORDER BY purchase_month;

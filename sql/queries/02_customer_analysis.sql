-- =====================================================================================
-- MODULE 2 : CUSTOMER INTELLIGENCE  (customer = customer_unique_id, NOT customer_id)
-- =====================================================================================

-- name: cus_repeat_rate
-- title: Repeat customer rate
-- question: What share of customers buy more than once?
-- level: basic
WITH customer_orders AS (
    SELECT customer_unique_id, COUNT(*) AS order_count
    FROM analytics.vw_delivered_orders GROUP BY customer_unique_id
)
SELECT COUNT(*) AS total_customers,
       COUNT(*) FILTER (WHERE order_count > 1) AS repeat_customers,
       ROUND(CAST(100.0 * COUNT(*) FILTER (WHERE order_count > 1) / NULLIF(COUNT(*), 0) AS NUMERIC), 2) AS repeat_customer_pct
FROM customer_orders;

-- name: cus_top_customers
-- title: Top 20 customers by lifetime spend
-- question: Who are our most valuable customers?
-- level: basic
SELECT customer_unique_id, customer_state,
       COUNT(*) AS orders,
       ROUND(CAST(SUM(item_revenue) AS NUMERIC), 2) AS lifetime_revenue,
       MIN(purchase_date) AS first_order, MAX(purchase_date) AS last_order
FROM analytics.vw_delivered_orders
GROUP BY customer_unique_id, customer_state
ORDER BY lifetime_revenue DESC
LIMIT 20;

-- name: cus_new_vs_returning
-- title: New vs returning customers by month
-- question: Is growth driven by acquisition or by retention?
-- level: advanced
WITH o AS (
    SELECT customer_unique_id, purchase_month,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchase_ts) AS order_seq
    FROM analytics.vw_delivered_orders
)
SELECT purchase_month AS month,
       COUNT(*) FILTER (WHERE order_seq = 1)  AS new_customer_orders,
       COUNT(*) FILTER (WHERE order_seq > 1)  AS returning_customer_orders,
       ROUND(CAST(100.0 * COUNT(*) FILTER (WHERE order_seq > 1) / COUNT(*) AS NUMERIC), 2) AS returning_share_pct
FROM o
GROUP BY purchase_month
ORDER BY purchase_month;

-- name: cus_rfm_scores
-- title: RFM scoring with NTILE (SQL version of the Python segmentation)
-- question: Which customers are recent, frequent and high-spending?
-- level: advanced
WITH base AS (
    SELECT customer_unique_id,
           (SELECT MAX(purchase_date) FROM analytics.vw_delivered_orders) + 1 - MAX(purchase_date) AS recency_days,
           COUNT(*) AS frequency,
           SUM(item_revenue) AS monetary
    FROM analytics.vw_delivered_orders GROUP BY customer_unique_id
), scored AS (
    SELECT *,
           6 - NTILE(5) OVER (ORDER BY recency_days) AS r_score,
           CASE WHEN frequency = 1 THEN 1 WHEN frequency = 2 THEN 3 ELSE 5 END AS f_score,
           NTILE(5) OVER (ORDER BY monetary) AS m_score
    FROM base
)
SELECT r_score, f_score, m_score,
       COUNT(*) AS customers,
       ROUND(CAST(AVG(monetary) AS NUMERIC), 2) AS avg_monetary
FROM scored
GROUP BY r_score, f_score, m_score
ORDER BY customers DESC
LIMIT 25;

-- name: cus_frequency_distribution
-- title: Purchase frequency distribution
-- question: How many customers buy once, twice, three times...?
-- level: basic
WITH f AS (SELECT customer_unique_id, COUNT(*) AS orders FROM analytics.vw_delivered_orders GROUP BY 1)
SELECT orders AS orders_placed, COUNT(*) AS customers,
       ROUND(CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC), 2) AS share_pct
FROM f GROUP BY orders ORDER BY orders;

-- name: cus_cohort_retention
-- title: Monthly cohort retention
-- question: Of the customers acquired in month X, how many buy again in month X+n?
-- level: advanced
WITH first_order AS (
    SELECT customer_unique_id, MIN(purchase_month) AS cohort_month
    FROM analytics.vw_delivered_orders GROUP BY customer_unique_id
), activity AS (
    SELECT DISTINCT f.cohort_month, o.customer_unique_id,
           (EXTRACT(YEAR FROM o.purchase_month) - EXTRACT(YEAR FROM f.cohort_month)) * 12
         + (EXTRACT(MONTH FROM o.purchase_month) - EXTRACT(MONTH FROM f.cohort_month)) AS month_index
    FROM analytics.vw_delivered_orders o
    JOIN first_order f USING (customer_unique_id)
)
SELECT cohort_month, month_index,
       COUNT(*) AS active_customers,
       FIRST_VALUE(COUNT(*)) OVER (PARTITION BY cohort_month ORDER BY month_index) AS cohort_size,
       ROUND(CAST(100.0 * COUNT(*) / FIRST_VALUE(COUNT(*)) OVER (PARTITION BY cohort_month ORDER BY month_index) AS NUMERIC), 2) AS retention_pct
FROM activity
GROUP BY cohort_month, month_index
ORDER BY cohort_month, month_index;

-- name: cus_geography
-- title: Customers and revenue per customer by state
-- question: Where do our customers live and where are they most valuable?
-- level: basic
SELECT customer_state AS state,
       COUNT(DISTINCT customer_unique_id) AS customers,
       ROUND(CAST(SUM(item_revenue) AS NUMERIC), 2) AS revenue,
       ROUND(CAST(SUM(item_revenue) / COUNT(DISTINCT customer_unique_id) AS NUMERIC), 2) AS revenue_per_customer
FROM analytics.vw_delivered_orders
GROUP BY customer_state
ORDER BY customers DESC;

-- name: cus_days_to_second_order
-- title: Days between first and second purchase
-- question: How long should a win-back campaign wait before nudging a customer?
-- level: advanced
WITH seq AS (
    SELECT customer_unique_id, purchase_date,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchase_ts) AS n,
           LEAD(purchase_date) OVER (PARTITION BY customer_unique_id ORDER BY purchase_ts) AS next_date
    FROM analytics.vw_delivered_orders
)
SELECT COUNT(*) AS customers_with_2nd_order,
       ROUND(CAST(AVG(next_date - purchase_date) AS NUMERIC), 1) AS avg_days_to_second_order,
       MIN(next_date - purchase_date) AS min_days,
       MAX(next_date - purchase_date) AS max_days
FROM seq
WHERE n = 1 AND next_date IS NOT NULL;

-- name: cus_value_deciles
-- title: Revenue concentration by customer decile
-- question: Do the top 10% of customers drive a disproportionate share of revenue?
-- level: advanced
WITH c AS (
    SELECT customer_unique_id, SUM(item_revenue) AS revenue FROM analytics.vw_delivered_orders GROUP BY 1
), d AS (
    SELECT *, NTILE(10) OVER (ORDER BY revenue DESC) AS decile FROM c
)
SELECT decile, COUNT(*) AS customers,
       ROUND(CAST(SUM(revenue) AS NUMERIC), 2) AS revenue,
       ROUND(CAST(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER () AS NUMERIC), 2) AS revenue_share_pct
FROM d GROUP BY decile ORDER BY decile;

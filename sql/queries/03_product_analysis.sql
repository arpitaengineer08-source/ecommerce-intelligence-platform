-- =====================================================================================
-- MODULE 3 : PRODUCT & CATEGORY INTELLIGENCE
-- =====================================================================================

-- name: prd_top_products
-- title: Top 10 products by revenue
-- question: Which individual products drive revenue?
-- level: basic
SELECT product_id, category,
       ROUND(CAST(SUM(price) AS NUMERIC), 2) AS revenue, COUNT(*) AS units_sold
FROM analytics.vw_delivered_items
GROUP BY product_id, category
ORDER BY revenue DESC
LIMIT 10;

-- name: prd_bottom_products
-- title: Bottom 10 products (min. 3 units sold)
-- question: Which products sell but contribute almost nothing?
-- level: basic
SELECT product_id, category,
       ROUND(CAST(SUM(price) AS NUMERIC), 2) AS revenue, COUNT(*) AS units_sold,
       ROUND(CAST(AVG(price) AS NUMERIC), 2) AS avg_price
FROM analytics.vw_delivered_items
GROUP BY product_id, category
HAVING COUNT(*) >= 3
ORDER BY revenue ASC
LIMIT 10;

-- name: prd_rank_in_category
-- title: Rank products within category (DENSE_RANK)
-- question: Who is the best-selling product in each category?
-- level: advanced
WITH product_sales AS (
    SELECT category, product_id, SUM(price) AS revenue
    FROM analytics.vw_delivered_items GROUP BY category, product_id
), ranked AS (
    SELECT *, DENSE_RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS category_rank
    FROM product_sales
)
SELECT category, product_id, ROUND(CAST(revenue AS NUMERIC), 2) AS revenue, category_rank
FROM ranked WHERE category_rank <= 3
ORDER BY category, category_rank;

-- name: prd_category_growth
-- title: Category growth, Jan-Aug 2018 vs Jan-Aug 2017
-- question: Which categories are growing fastest and which are shrinking?
-- level: advanced
WITH y AS (
    SELECT category,
           SUM(price) FILTER (WHERE EXTRACT(YEAR FROM purchase_month) = 2017 AND EXTRACT(MONTH FROM purchase_month) <= 8) AS rev_2017,
           SUM(price) FILTER (WHERE EXTRACT(YEAR FROM purchase_month) = 2018) AS rev_2018
    FROM analytics.vw_delivered_items GROUP BY category
)
SELECT category,
       ROUND(CAST(rev_2017 AS NUMERIC), 2) AS revenue_2017,
       ROUND(CAST(rev_2018 AS NUMERIC), 2) AS revenue_2018,
       ROUND(CAST(100.0 * (rev_2018 / NULLIF(rev_2017, 0) - 1) AS NUMERIC), 1) AS growth_pct
FROM y
WHERE rev_2017 IS NOT NULL AND rev_2018 IS NOT NULL
ORDER BY growth_pct DESC;

-- name: prd_price_distribution
-- title: Selling price distribution by category (median, P90)
-- question: Which categories are premium vs budget?
-- level: advanced
SELECT category,
       COUNT(*) AS units,
       ROUND(CAST(AVG(price) AS NUMERIC), 2) AS avg_price,
       ROUND(CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS NUMERIC), 2) AS median_price,
       ROUND(CAST(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY price) AS NUMERIC), 2) AS p90_price
FROM analytics.vw_delivered_items
GROUP BY category
HAVING COUNT(*) >= 30
ORDER BY avg_price DESC;

-- name: prd_revenue_concentration
-- title: How many products generate 80% of revenue?
-- question: Is the catalogue healthy or dependent on a few hero products?
-- level: advanced
WITH p AS (
    SELECT product_id, SUM(price) AS revenue FROM analytics.vw_delivered_items GROUP BY product_id
), cum AS (
    SELECT product_id, revenue,
           SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER () AS cum_share,
           ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rn
    FROM p
)
SELECT COUNT(*) AS products_selling,
       (SELECT MIN(rn) FROM cum WHERE cum_share >= 0.8) AS products_for_80pct_revenue,
       ROUND(CAST(100.0 * (SELECT MIN(rn) FROM cum WHERE cum_share >= 0.8) / COUNT(*) AS NUMERIC), 1) AS pct_of_catalogue
FROM cum;

-- name: prd_category_cancellation
-- title: Cancellation / unavailability rate by category
-- question: Which categories have fulfilment problems?
-- level: basic
SELECT dp.category,
       COUNT(*) AS items,
       COUNT(*) FILTER (WHERE fi.order_status IN ('canceled', 'unavailable')) AS failed_items,
       ROUND(CAST(100.0 * COUNT(*) FILTER (WHERE fi.order_status IN ('canceled', 'unavailable')) / COUNT(*) AS NUMERIC), 2) AS failure_rate_pct
FROM analytics.fact_order_items fi
JOIN analytics.dim_product dp ON dp.product_id = fi.product_id
GROUP BY dp.category
HAVING COUNT(*) >= 100
ORDER BY failure_rate_pct DESC;

-- name: prd_declining_categories
-- title: Underperforming category detection (last 3 vs previous 3 full months)
-- question: Which categories are losing momentum right now?
-- level: advanced
WITH months AS (
    SELECT DISTINCT purchase_month FROM analytics.vw_delivered_items ORDER BY 1 DESC LIMIT 7
), ranked AS (
    SELECT purchase_month, DENSE_RANK() OVER (ORDER BY purchase_month DESC) AS rk FROM months
), cat AS (
    SELECT i.category,
           SUM(i.price) FILTER (WHERE r.rk BETWEEN 2 AND 4) AS last_3m,
           SUM(i.price) FILTER (WHERE r.rk BETWEEN 5 AND 7) AS prev_3m
    FROM analytics.vw_delivered_items i JOIN ranked r USING (purchase_month)
    GROUP BY i.category
)
SELECT category,
       ROUND(CAST(prev_3m AS NUMERIC), 2) AS previous_3m_revenue,
       ROUND(CAST(last_3m AS NUMERIC), 2) AS last_3m_revenue,
       ROUND(CAST(100.0 * (last_3m / NULLIF(prev_3m, 0) - 1) AS NUMERIC), 1) AS change_pct
FROM cat
WHERE prev_3m > 0
ORDER BY change_pct ASC;

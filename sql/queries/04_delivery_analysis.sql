-- =====================================================================================
-- MODULE 4 : ORDER & DELIVERY ANALYTICS
-- =====================================================================================

-- name: del_monthly_performance
-- title: Delivery time and late-delivery rate by month
-- question: Is fulfilment getting better or worse?
-- level: basic
SELECT purchase_month AS month,
       COUNT(*) AS delivered_orders,
       ROUND(CAST(AVG(delivery_days) AS NUMERIC), 2)      AS avg_delivery_days,
       ROUND(CAST(AVG(estimated_days) AS NUMERIC), 2)     AS avg_estimated_days,
       ROUND(CAST(100.0 * AVG(is_late) AS NUMERIC), 2)    AS late_pct
FROM analytics.vw_delivered_orders
WHERE delivered_ts IS NOT NULL
GROUP BY purchase_month ORDER BY purchase_month;

-- name: del_by_state
-- title: Estimated vs actual delivery by customer state
-- question: Which states experience the slowest or least reliable delivery?
-- level: basic
SELECT customer_state AS state, COUNT(*) AS orders,
       ROUND(CAST(AVG(delivery_days) AS NUMERIC), 1)   AS avg_actual_days,
       ROUND(CAST(AVG(estimated_days) AS NUMERIC), 1)  AS avg_estimated_days,
       ROUND(CAST(100.0 * AVG(is_late) AS NUMERIC), 2) AS late_pct
FROM analytics.vw_delivered_orders
WHERE delivered_ts IS NOT NULL
GROUP BY customer_state
HAVING COUNT(*) >= 50
ORDER BY avg_actual_days DESC;

-- name: del_by_region
-- title: Regional delivery performance
-- question: How large is the delivery gap between regions?
-- level: basic
SELECT g.region, COUNT(*) AS orders,
       ROUND(CAST(AVG(fo.delivery_days) AS NUMERIC), 1)   AS avg_delivery_days,
       ROUND(CAST(100.0 * AVG(fo.is_late) AS NUMERIC), 2) AS late_pct,
       ROUND(CAST(AVG(fo.freight_value) AS NUMERIC), 2)   AS avg_freight
FROM analytics.vw_delivered_orders fo
JOIN analytics.dim_geography g ON g.state = fo.customer_state
WHERE fo.delivered_ts IS NOT NULL
GROUP BY g.region ORDER BY avg_delivery_days DESC;

-- name: del_seller_late_ranking
-- title: Sellers ranked by late-delivery rate (>= 30 orders)
-- question: Which sellers hurt the customer experience?
-- level: advanced
WITH s AS (
    SELECT fi.seller_id, COUNT(DISTINCT fo.order_id) AS orders,
           AVG(fo.is_late) AS late_rate, AVG(fo.delivery_days) AS avg_days
    FROM analytics.fact_order_items fi
    JOIN analytics.vw_delivered_orders fo ON fo.order_id = fi.order_id
    WHERE fo.delivered_ts IS NOT NULL
    GROUP BY fi.seller_id HAVING COUNT(DISTINCT fo.order_id) >= 30
)
SELECT seller_id, orders,
       ROUND(CAST(100.0 * late_rate AS NUMERIC), 2) AS late_pct,
       ROUND(CAST(avg_days AS NUMERIC), 1) AS avg_delivery_days,
       RANK() OVER (ORDER BY late_rate DESC) AS late_rank
FROM s ORDER BY late_rank LIMIT 20;

-- name: del_freight_by_category
-- title: Freight as % of item price by category
-- question: Where does shipping eat into the customer's basket?
-- level: basic
SELECT category, COUNT(*) AS units,
       ROUND(CAST(AVG(freight_value) AS NUMERIC), 2) AS avg_freight,
       ROUND(CAST(100.0 * SUM(freight_value) / SUM(price) AS NUMERIC), 1) AS freight_pct_of_price
FROM analytics.vw_delivered_items
GROUP BY category HAVING COUNT(*) >= 100
ORDER BY freight_pct_of_price DESC;

-- name: del_time_buckets
-- title: Delivery time buckets
-- question: How is delivery time distributed?
-- level: basic
SELECT CASE WHEN delivery_days <= 5 THEN '1. 0-5 days'
            WHEN delivery_days <= 10 THEN '2. 6-10 days'
            WHEN delivery_days <= 15 THEN '3. 11-15 days'
            WHEN delivery_days <= 20 THEN '4. 16-20 days'
            ELSE '5. 21+ days' END AS delivery_bucket,
       COUNT(*) AS orders,
       ROUND(CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC), 2) AS share_pct
FROM analytics.vw_delivered_orders
WHERE delivered_ts IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- name: del_seller_scorecard
-- title: Seller scorecard (revenue, late rate, review score)
-- question: Which high-revenue sellers also deliver a poor experience?
-- level: advanced
WITH seller_orders AS (
    SELECT DISTINCT fi.seller_id, fo.order_id, fo.is_late, fo.avg_review_score
    FROM analytics.fact_order_items fi JOIN analytics.vw_delivered_orders fo ON fo.order_id = fi.order_id
), rev AS (
    SELECT seller_id, SUM(price) AS revenue FROM analytics.vw_delivered_items GROUP BY seller_id
), perf AS (
    SELECT seller_id, COUNT(*) AS orders, AVG(is_late) AS late_rate, AVG(avg_review_score) AS avg_review
    FROM seller_orders GROUP BY seller_id HAVING COUNT(*) >= 30
)
SELECT p.seller_id, ds.seller_state, p.orders,
       ROUND(CAST(r.revenue AS NUMERIC), 2) AS revenue,
       ROUND(CAST(100.0 * p.late_rate AS NUMERIC), 2) AS late_pct,
       ROUND(CAST(p.avg_review AS NUMERIC), 2) AS avg_review,
       CASE WHEN p.late_rate > 0.15 OR p.avg_review < 3.8 THEN 'Review' WHEN p.late_rate < 0.05 AND p.avg_review >= 4.3 THEN 'Star' ELSE 'OK' END AS status
FROM perf p JOIN rev r USING (seller_id) JOIN analytics.dim_seller ds USING (seller_id)
ORDER BY r.revenue DESC LIMIT 25;

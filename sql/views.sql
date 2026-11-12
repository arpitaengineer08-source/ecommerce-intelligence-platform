-- Reusable analytical views (business-friendly layer used by queries, Streamlit and Power BI)
DROP VIEW IF EXISTS analytics.vw_delivered_orders;
CREATE VIEW analytics.vw_delivered_orders AS
SELECT * FROM analytics.fact_orders WHERE order_status = 'delivered';

DROP VIEW IF EXISTS analytics.vw_delivered_items;
CREATE VIEW analytics.vw_delivered_items AS
SELECT fi.*, dp.category FROM analytics.fact_order_items fi
JOIN analytics.dim_product dp ON dp.product_id = fi.product_id
WHERE fi.order_status = 'delivered';

DROP VIEW IF EXISTS analytics.vw_monthly_kpis;
CREATE VIEW analytics.vw_monthly_kpis AS
SELECT purchase_month,
       COUNT(*)                         AS orders,
       SUM(item_revenue)                AS revenue,
       SUM(item_revenue) / COUNT(*)     AS aov,
       COUNT(DISTINCT customer_unique_id) AS customers
FROM analytics.vw_delivered_orders
GROUP BY purchase_month;

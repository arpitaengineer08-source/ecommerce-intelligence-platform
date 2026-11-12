-- =====================================================================================
-- Builds the ANALYTICS star schema from the STAGING (cleaned) tables.
-- dim_date and dim_geography are loaded by Python (analytics.dim_date / dim_geography).
--
-- GRAIN (kept separate to avoid fan-out when joining payments / reviews / items):
--   fact_order_items : 1 row per order item      fact_orders  : 1 row per order
--   fact_payments    : 1 row per payment record   fact_reviews : 1 row per review
-- =====================================================================================

DROP TABLE IF EXISTS analytics.dim_customer;
CREATE TABLE analytics.dim_customer AS
SELECT customer_unique_id,
       MIN(customer_city)            AS customer_city,
       MIN(customer_state)           AS customer_state,
       MIN(customer_zip_code_prefix) AS customer_zip_code_prefix
FROM staging.customers
GROUP BY customer_unique_id;

DROP TABLE IF EXISTS analytics.dim_product;
CREATE TABLE analytics.dim_product AS
SELECT p.product_id,
       p.product_category_name                                   AS category_pt,
       COALESCE(t.product_category_name_english, p.product_category_name) AS category,
       p.product_weight_g, p.product_photos_qty
FROM staging.products p
LEFT JOIN staging.category_translation t ON t.product_category_name = p.product_category_name;

DROP TABLE IF EXISTS analytics.dim_seller;
CREATE TABLE analytics.dim_seller AS
SELECT seller_id, seller_city, seller_state FROM staging.sellers;

DROP TABLE IF EXISTS analytics.fact_orders;
CREATE TABLE analytics.fact_orders AS
WITH items AS (
    SELECT order_id, SUM(price) AS item_revenue, SUM(freight_value) AS freight_value, COUNT(*) AS items_count
    FROM staging.order_items GROUP BY order_id
), pay AS (
    SELECT order_id, SUM(payment_value) AS payment_value, MAX(payment_installments) AS max_installments
    FROM staging.payments GROUP BY order_id
), rev AS (
    SELECT order_id, AVG(review_score) AS avg_review_score FROM staging.reviews GROUP BY order_id
)
SELECT o.order_id,
       c.customer_unique_id,
       c.customer_state,
       c.customer_city,
       o.order_status,
       o.order_purchase_timestamp                             AS purchase_ts,
       CAST(o.order_purchase_timestamp AS DATE)               AS purchase_date,
       CAST(DATE_TRUNC('month', o.order_purchase_timestamp) AS DATE) AS purchase_month,
       o.order_delivered_carrier_date                         AS carrier_ts,
       o.order_delivered_customer_date                        AS delivered_ts,
       o.order_estimated_delivery_date                        AS estimated_ts,
       CAST(o.order_delivered_customer_date AS DATE) - CAST(o.order_purchase_timestamp AS DATE)  AS delivery_days,
       CAST(o.order_estimated_delivery_date AS DATE) - CAST(o.order_purchase_timestamp AS DATE)  AS estimated_days,
       CAST(o.order_delivered_customer_date AS DATE) - CAST(o.order_estimated_delivery_date AS DATE) AS delivery_delay_days,
       CASE WHEN o.order_delivered_customer_date IS NULL THEN NULL
            WHEN CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE) THEN 1 ELSE 0 END AS is_late,
       COALESCE(i.item_revenue, 0)  AS item_revenue,
       COALESCE(i.freight_value, 0) AS freight_value,
       COALESCE(i.items_count, 0)   AS items_count,
       pay.payment_value, pay.max_installments, rev.avg_review_score
FROM staging.orders o
JOIN staging.customers c ON c.customer_id = o.customer_id
LEFT JOIN items i   ON i.order_id = o.order_id
LEFT JOIN pay       ON pay.order_id = o.order_id
LEFT JOIN rev       ON rev.order_id = o.order_id;

DROP TABLE IF EXISTS analytics.fact_order_items;
CREATE TABLE analytics.fact_order_items AS
SELECT oi.order_id, oi.order_item_id, oi.product_id, oi.seller_id,
       fo.customer_unique_id, fo.customer_state, fo.order_status, fo.purchase_date, fo.purchase_month,
       oi.price, oi.freight_value
FROM staging.order_items oi
JOIN analytics.fact_orders fo ON fo.order_id = oi.order_id;

DROP TABLE IF EXISTS analytics.fact_payments;
CREATE TABLE analytics.fact_payments AS
SELECT order_id, payment_sequential, payment_type, payment_installments, payment_value FROM staging.payments;

DROP TABLE IF EXISTS analytics.fact_reviews;
CREATE TABLE analytics.fact_reviews AS
SELECT review_id, order_id, review_score, review_comment_message,
       CAST(review_creation_date AS DATE) AS review_date,
       CAST(DATE_TRUNC('month', review_creation_date) AS DATE) AS review_month
FROM staging.reviews;

-- =====================================================================================
-- MODULES 5 & 6 : PAYMENT INTELLIGENCE  +  CUSTOMER SATISFACTION
-- =====================================================================================

-- name: pay_by_method
-- title: Revenue and transaction value by payment method
-- question: Which payment methods matter most?
-- level: basic
SELECT fp.payment_type,
       COUNT(*) AS transactions,
       ROUND(CAST(SUM(fp.payment_value) AS NUMERIC), 2) AS total_value,
       ROUND(CAST(AVG(fp.payment_value) AS NUMERIC), 2) AS avg_transaction_value,
       ROUND(CAST(100.0 * SUM(fp.payment_value) / SUM(SUM(fp.payment_value)) OVER () AS NUMERIC), 2) AS share_pct
FROM analytics.fact_payments fp
JOIN analytics.vw_delivered_orders fo ON fo.order_id = fp.order_id
GROUP BY fp.payment_type ORDER BY total_value DESC;

-- name: pay_installments
-- title: Credit-card instalment analysis
-- question: Do larger baskets rely on instalments?
-- level: basic
SELECT payment_installments AS installments, COUNT(*) AS payments,
       ROUND(CAST(AVG(payment_value) AS NUMERIC), 2) AS avg_payment_value,
       ROUND(CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC), 2) AS share_pct
FROM analytics.fact_payments WHERE payment_type = 'credit_card'
GROUP BY payment_installments ORDER BY payment_installments;

-- name: pay_freight_contribution
-- title: Freight contribution to order value by month
-- question: How much of what customers pay is shipping?
-- level: basic
SELECT purchase_month AS month,
       ROUND(CAST(SUM(item_revenue) AS NUMERIC), 2) AS item_revenue,
       ROUND(CAST(SUM(freight_value) AS NUMERIC), 2) AS freight_revenue,
       ROUND(CAST(100.0 * SUM(freight_value) / NULLIF(SUM(item_revenue), 0) AS NUMERIC), 2) AS freight_pct_of_items
FROM analytics.vw_delivered_orders GROUP BY purchase_month ORDER BY purchase_month;

-- name: pay_by_rfm_segment
-- title: Payment behaviour by customer segment (needs Python RFM table)
-- question: Do champions pay differently from at-risk customers?
-- level: advanced
SELECT r.segment,
       COUNT(DISTINCT r.customer_unique_id) AS customers,
       ROUND(CAST(AVG(fo.max_installments) AS NUMERIC), 2) AS avg_max_installments,
       ROUND(CAST(100.0 * COUNT(*) FILTER (WHERE fp.payment_type = 'credit_card') / COUNT(*) AS NUMERIC), 1) AS credit_card_pct,
       ROUND(CAST(AVG(fp.payment_value) AS NUMERIC), 2) AS avg_payment_value
FROM analytics.rfm_segments r
JOIN analytics.vw_delivered_orders fo ON fo.customer_unique_id = r.customer_unique_id
JOIN analytics.fact_payments fp ON fp.order_id = fo.order_id
GROUP BY r.segment ORDER BY customers DESC;

-- name: sat_score_distribution
-- title: Review score distribution
-- question: How satisfied are customers overall?
-- level: basic
SELECT review_score, COUNT(*) AS reviews,
       ROUND(CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC), 2) AS share_pct
FROM analytics.fact_reviews GROUP BY review_score ORDER BY review_score;

-- name: sat_delay_vs_rating
-- title: Delivery delay vs review score
-- question: How much does a late delivery hurt the rating?
-- level: advanced
SELECT CASE WHEN fo.delivery_delay_days <= -10 THEN '1. 10+ days early'
            WHEN fo.delivery_delay_days <= -1  THEN '2. 1-9 days early'
            WHEN fo.delivery_delay_days = 0    THEN '3. on estimate day'
            WHEN fo.delivery_delay_days <= 5   THEN '4. 1-5 days late'
            ELSE '5. 6+ days late' END AS delivery_vs_estimate,
       COUNT(*) AS orders,
       ROUND(CAST(AVG(fo.avg_review_score) AS NUMERIC), 2) AS avg_review_score,
       ROUND(CAST(100.0 * COUNT(*) FILTER (WHERE fo.avg_review_score <= 2) / COUNT(*) AS NUMERIC), 1) AS low_rating_pct
FROM analytics.vw_delivered_orders fo
WHERE fo.delivered_ts IS NOT NULL AND fo.avg_review_score IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- name: sat_low_rated_categories
-- title: Lowest-rated categories (>= 100 reviews)
-- question: Which categories disappoint customers most?
-- level: advanced
SELECT dp.category, COUNT(*) AS reviews,
       ROUND(CAST(AVG(fr.review_score) AS NUMERIC), 2) AS avg_score,
       ROUND(CAST(100.0 * COUNT(*) FILTER (WHERE fr.review_score <= 2) / COUNT(*) AS NUMERIC), 1) AS low_rating_pct
FROM analytics.fact_reviews fr
JOIN (SELECT DISTINCT order_id, product_id FROM analytics.fact_order_items) fi ON fi.order_id = fr.order_id
JOIN analytics.dim_product dp ON dp.product_id = fi.product_id
GROUP BY dp.category HAVING COUNT(*) >= 100
ORDER BY avg_score ASC;

-- name: sat_monthly_trend
-- title: Review score trend by month
-- question: Is customer satisfaction improving?
-- level: basic
SELECT review_month AS month, COUNT(*) AS reviews,
       ROUND(CAST(AVG(review_score) AS NUMERIC), 3) AS avg_score,
       ROUND(CAST(100.0 * COUNT(*) FILTER (WHERE review_score <= 2) / COUNT(*) AS NUMERIC), 2) AS low_rating_pct
FROM analytics.fact_reviews GROUP BY review_month ORDER BY review_month;

-- name: sat_complaint_themes
-- title: Recurring complaint themes in low-score comments (keyword rules, PT + EN)
-- question: Why are unhappy customers unhappy?
-- level: advanced
SELECT CASE WHEN LOWER(review_comment_message) LIKE '%atras%' OR LOWER(review_comment_message) LIKE '%demor%' OR LOWER(review_comment_message) LIKE '%nao recebi%' OR LOWER(review_comment_message) LIKE '%não recebi%' OR LOWER(review_comment_message) LIKE '%late%' THEN 'Late / missing delivery'
            WHEN LOWER(review_comment_message) LIKE '%quebrad%' OR LOWER(review_comment_message) LIKE '%defeito%' OR LOWER(review_comment_message) LIKE '%damaged%' THEN 'Damaged / defective'
            WHEN LOWER(review_comment_message) LIKE '%qualidade%' OR LOWER(review_comment_message) LIKE '%diferente%' OR LOWER(review_comment_message) LIKE '%quality%' THEN 'Quality / not as described'
            WHEN LOWER(review_comment_message) LIKE '%vendedor%' OR LOWER(review_comment_message) LIKE '%respond%' OR LOWER(review_comment_message) LIKE '%faltou%' THEN 'Seller service / missing item'
            ELSE 'Other' END AS theme,
       COUNT(*) AS comments
FROM analytics.fact_reviews
WHERE review_score <= 2 AND review_comment_message IS NOT NULL
GROUP BY 1 ORDER BY comments DESC;

-- PostgreSQL only (run automatically when DATABASE_URL is set): enforce keys on the star schema.
ALTER TABLE analytics.dim_customer     ADD PRIMARY KEY (customer_unique_id);
ALTER TABLE analytics.dim_product      ADD PRIMARY KEY (product_id);
ALTER TABLE analytics.dim_seller       ADD PRIMARY KEY (seller_id);
ALTER TABLE analytics.dim_date         ADD PRIMARY KEY (date_key);
ALTER TABLE analytics.dim_geography    ADD PRIMARY KEY (state);
ALTER TABLE analytics.fact_orders      ADD PRIMARY KEY (order_id);
ALTER TABLE analytics.fact_order_items ADD PRIMARY KEY (order_id, order_item_id);
ALTER TABLE analytics.fact_payments    ADD PRIMARY KEY (order_id, payment_sequential);
ALTER TABLE analytics.fact_reviews     ADD PRIMARY KEY (review_id, order_id);
CREATE INDEX idx_fo_month    ON analytics.fact_orders (purchase_month);
CREATE INDEX idx_fo_customer ON analytics.fact_orders (customer_unique_id);
CREATE INDEX idx_fi_product  ON analytics.fact_order_items (product_id);
CREATE INDEX idx_fi_seller   ON analytics.fact_order_items (seller_id);

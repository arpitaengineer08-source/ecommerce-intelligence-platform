# Data Quality Report

_Generated 2026-11-12 15:21 | data source: **synthetic**_

**30/31 checks passed** | 1 warnings | 0 failures

## 1. Validation checks

| Status | Check | Table | Detail |
|---|---|---|---|
| PASS | Primary key unique (customer_id) | customers | 0 duplicate keys |
| PASS | Primary key unique (order_id) | orders | 0 duplicate keys |
| PASS | Primary key unique (order_id+order_item_id) | order_items | 0 duplicate keys |
| PASS | Primary key unique (order_id+payment_sequential) | payments | 0 duplicate keys |
| PASS | Primary key unique (product_id) | products | 0 duplicate keys |
| PASS | Primary key unique (seller_id) | sellers | 0 duplicate keys |
| PASS | Primary key unique (review_id+order_id) | reviews | 0 duplicate keys |
| PASS | Foreign key: orders.customer_id -> customers | orders | 0 orphan rows |
| PASS | Foreign key: order_items.order_id -> orders | order_items | 0 orphan rows |
| PASS | Foreign key: order_items.product_id -> products | order_items | 0 orphan rows |
| PASS | Foreign key: order_items.seller_id -> sellers | order_items | 0 orphan rows |
| PASS | Foreign key: payments.order_id -> orders | payments | 0 orphan rows |
| PASS | Foreign key: reviews.order_id -> orders | reviews | 0 orphan rows |
| PASS | No nulls in order_purchase_timestamp | orders | 0 nulls |
| PASS | No nulls in price | order_items | 0 nulls |
| PASS | No nulls in customer_unique_id | customers | 0 nulls |
| PASS | Products with known category | products | 50 unknown (1.4%) |
| WARN | Delivered orders have delivery date | orders | 15 missing |
| PASS | Carrier pickup not before purchase | orders | 0 violations |
| PASS | Review score within 1-5 | reviews | range check |
| PASS | Prices strictly positive | order_items | 0 non-positive |
| PASS | Payments reconcile with items + freight (+-R$1) | payments | 0.00% of orders mismatch |
| PASS | Row-count drift vs last run (<20%) | customers | 22,000 -> 22,000 (+0.0%) |
| PASS | Row-count drift vs last run (<20%) | orders | 22,000 -> 22,000 (+0.0%) |
| PASS | Row-count drift vs last run (<20%) | order_items | 25,470 -> 25,470 (+0.0%) |
| PASS | Row-count drift vs last run (<20%) | payments | 23,075 -> 23,075 (+0.0%) |
| PASS | Row-count drift vs last run (<20%) | reviews | 21,585 -> 21,585 (+0.0%) |
| PASS | Row-count drift vs last run (<20%) | products | 3,500 -> 3,500 (+0.0%) |
| PASS | Row-count drift vs last run (<20%) | sellers | 600 -> 600 (+0.0%) |
| PASS | Row-count drift vs last run (<20%) | geolocation | 1,599 -> 1,599 (+0.0%) |
| PASS | Row-count drift vs last run (<20%) | category_translation | 22 -> 22 (+0.0%) |

## 2. Cleaning actions applied

| Table | Issue | Rows | Action |
|---|---|---|---|
| orders | delivered before purchase (impossible) | 15 | delivery date set to NULL, order kept |
| orders | status=delivered but no delivery date | 15 | kept (excluded from delivery-time metrics) |
| reviews | fully duplicated rows | 60 | dropped |
| products | missing category | 50 | filled with 'unknown' |
| geolocation | many rows per zip prefix | 21 | aggregated to 1 row per zip prefix |

## 3. Known dataset limitations

- No product cost data -> **profit/margin cannot be computed**; revenue and freight only.
- No inventory snapshots -> **stock-out risk cannot be measured**.
- No web sessions / cart events -> **conversion and cart abandonment are not available**.
- `customer_id` is per-order; `customer_unique_id` is used to identify real customers.
- **Data source is synthetic** (Olist-schema generator). Replace with the real Olist CSVs for real insights.
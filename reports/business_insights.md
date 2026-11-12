# Business Insights & Recommendations

_Auto-generated 2026-11-12 15:22 | data source: **synthetic**_

> **Note:** numbers below come from the synthetic Olist-style dataset. Run the pipeline with the real Olist CSVs (`python run_pipeline.py --real`) to regenerate this report with real findings.

## Headline KPIs

| KPI | Value |
|---|---|
| Delivered revenue | R$3,129,213 |
| Delivered orders | 21,227 |
| Unique customers | 20,332 |
| Average order value | R$147.42 |
| Repeat customer rate | 4.02% |
| Cancellation rate | 1.27% |
| Late delivery rate | 5.64% |
| Average review score | 4.27 / 5 |

## Business Recommendations

### 1. Revenue is scaling, with a single seasonal spike  _(priority: High | Executive)_

**What the data shows:** Average monthly revenue grew from R$72,733 (first 6 months) to R$231,061 (latest 6 months), +218%. The peak month was Nov 2017 at R$267,775.

**Why it matters:** A one-month spike inflates averages and can hide whether the underlying trend is healthy.

**Recommended action:** Plan inventory, seller capacity and logistics for the peak period at least 8 weeks ahead, and judge growth on rolling 3-month averages rather than single months.

### 2. Categories losing momentum  _(priority: High | Product)_

**What the data shows:** Revenue over the last 3 full months versus the prior 3 months fell in: books_general_interest (-51%).

**Why it matters:** Falling categories may signal pricing, availability or demand problems, but the data alone cannot say which.

**Recommended action:** Investigate pricing versus competitors, stock availability and review scores before spending more on promotion. Re-test after one quarter.

### 3. Very few customers come back  _(priority: High | Customer)_

**What the data shows:** Only 4.0% of 20,332 customers placed a second order; those who did returned after 141 days on average.

**Why it matters:** Acquisition-only growth is expensive. Even small gains in repeat rate compound across a large customer base.

**Recommended action:** Launch a post-purchase journey that offers a second-order incentive around day 20-30 and target categories with natural repurchase (health & beauty, pet, perfumery).

### 4. Late delivery is strongly linked to bad reviews  _(priority: High | Operations)_

**What the data shows:** Orders that arrive on time or early average 4.39 stars versus 1.76 when 6+ days late. Overall late-delivery rate is about 5.6%.

**Why it matters:** Delivery delay is strongly associated with low ratings, so fixing logistics is likely the fastest lever for better reviews (confirm with an A/B test on delivery estimates).

**Recommended action:** Set seller SLAs and padding on delivery estimates in slow regions, and escalate sellers who breach them repeatedly.

### 5. High-value customers are drifting away  _(priority: High | Customer)_

**What the data shows:** 1,204 high-spending customers are 60-180 days past their last order, holding R$477,099 in historical spend.

**Why it matters:** These customers are cheaper to win back than new customers are to acquire.

**Recommended action:** Send personalised win-back offers before day 180 and measure the response against a holdout group.

### 6. Revenue concentrated in a few categories  _(priority: Medium | Product)_

**What the data shows:** The top 3 categories (watches_gifts, health_beauty, bed_bath_table) contribute 30.6% of revenue.

**Why it matters:** High concentration raises exposure to demand shocks and seller issues in a few categories.

**Recommended action:** Protect the top categories (availability, delivery SLAs) while testing targeted growth in mid-sized categories with rising trend.

### 7. A small group of sellers delivers late far more often  _(priority: Medium | Operations)_

**What the data shows:** The worst 5 sellers (30+ orders) are late on 25% of orders versus a platform average of about 6%.

**Why it matters:** A few poor performers damage the brand for every customer who buys from them.

**Recommended action:** Place high-late-rate sellers on a performance plan, reduce their search ranking until they recover, and share seller scorecards monthly.

### 8. Large delivery-time gap between regions  _(priority: Medium | Operations)_

**What the data shows:** North averages 17.8 days to deliver versus 8.2 days in Southeast.

**Why it matters:** Slow regions suffer worse customer experience and higher freight cost, which can suppress demand there.

**Recommended action:** Evaluate regional fulfilment hubs or carrier changes for the slowest region, and investigate whether low sales there come from demand or delivery friction.

### 9. Cancellations quietly leak revenue  _(priority: Medium | Executive)_

**What the data shows:** Cancelled and unavailable orders represent R$39,947 of item value, about 1.3% of potential revenue.

**Why it matters:** Unavailable items point to stock-sync problems between sellers and the marketplace.

**Recommended action:** Require sellers to confirm stock at checkout and penalise repeated 'unavailable' cancellations.

### 10. Short-term revenue outlook  _(priority: Medium | Predictive)_

**What the data shows:** The best model on hold-out data (Holt damped trend, MAPE 3.1%) projects R$821,923 over the next 3 months.

**Why it matters:** The forecast gives a planning baseline but does not capture holidays or promotions if history is short.

**Recommended action:** Use it as the base case for capacity planning and add judgement for known campaigns; refresh monthly and monitor forecast error.

### 11. Credit cards and instalments dominate payments  _(priority: Low | Revenue)_

**What the data shows:** Credit cards account for 76.8% of payment value; boleto is the main alternative.

**Why it matters:** Instalments let customers afford larger baskets, but boleto customers abandon more often in many marketplaces (not measurable here).

**Recommended action:** Keep instalment options visible on higher-priced items, and test boleto reminders to reduce unpaid orders.

## What this analysis cannot tell you

- Profit and margin (no cost data), stock-out risk (no inventory data), conversion and cart abandonment (no web events).
- Causality: patterns such as late delivery vs ratings are associations; confirm with experiments before large investments.
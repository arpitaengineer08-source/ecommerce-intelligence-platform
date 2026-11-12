# DAX measures

Create a blank table called `_Measures` (Home > Enter data) and add these measures to it. Table names assume the CSVs from
`data/processed/powerbi/` were imported with the names `Fact_Orders`, `Fact_Order_Items`, `Fact_Payments`, `Fact_Reviews`,
`Dim_Date`, `Dim_Customer`, `Dim_Product`, `Dim_Seller`, `Dim_Geography`, `RFM_Segments`.

> Mark `Dim_Date` as a date table (Table tools > Mark as date table > `date_key`).

## Core revenue

```dax
Total Revenue =
CALCULATE ( SUM ( Fact_Order_Items[price] ), Fact_Order_Items[order_status] = "delivered" )

Delivered Orders =
CALCULATE ( DISTINCTCOUNT ( Fact_Order_Items[order_id] ), Fact_Order_Items[order_status] = "delivered" )

Average Order Value = DIVIDE ( [Total Revenue], [Delivered Orders], 0 )

Freight Value =
CALCULATE ( SUM ( Fact_Order_Items[freight_value] ), Fact_Order_Items[order_status] = "delivered" )

Freight % of Item Revenue = DIVIDE ( [Freight Value], [Total Revenue], 0 )

Units Sold =
CALCULATE ( COUNTROWS ( Fact_Order_Items ), Fact_Order_Items[order_status] = "delivered" )

Average Selling Price = DIVIDE ( [Total Revenue], [Units Sold], 0 )

Revenue by Category % =
DIVIDE ( [Total Revenue], CALCULATE ( [Total Revenue], ALL ( Dim_Product[category] ) ), 0 )
```

## Time intelligence

```dax
Revenue Previous Month = CALCULATE ( [Total Revenue], DATEADD ( Dim_Date[date_key], -1, MONTH ) )

MoM Growth % =
DIVIDE ( [Total Revenue] - [Revenue Previous Month], [Revenue Previous Month] )

Revenue Previous Year = CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( Dim_Date[date_key] ) )

YoY Growth % =
DIVIDE ( [Total Revenue] - [Revenue Previous Year], [Revenue Previous Year] )

Revenue 3M Rolling Avg =
AVERAGEX ( DATESINPERIOD ( Dim_Date[date_key], MAX ( Dim_Date[date_key] ), -3, MONTH ), [Total Revenue] )

Revenue YTD = TOTALYTD ( [Total Revenue], Dim_Date[date_key] )
```

## Orders and cancellations

```dax
Total Orders = DISTINCTCOUNT ( Fact_Orders[order_id] )

Cancelled Orders =
CALCULATE ( DISTINCTCOUNT ( Fact_Orders[order_id] ), Fact_Orders[order_status] IN { "canceled", "unavailable" } )

Cancellation Rate % = DIVIDE ( [Cancelled Orders], [Total Orders], 0 )

Lost Revenue (Cancelled) =
CALCULATE ( SUM ( Fact_Orders[item_revenue] ), Fact_Orders[order_status] IN { "canceled", "unavailable" } )
```

## Customers

```dax
Total Customers =
CALCULATE ( DISTINCTCOUNT ( Fact_Orders[customer_unique_id] ), Fact_Orders[order_status] = "delivered" )

Repeat Customers =
COUNTROWS (
    FILTER (
        VALUES ( Fact_Orders[customer_unique_id] ),
        CALCULATE ( COUNTROWS ( Fact_Orders ), Fact_Orders[order_status] = "delivered" ) > 1
    )
)

Repeat Customer Rate % = DIVIDE ( [Repeat Customers], [Total Customers], 0 )

Avg Purchase Frequency =
DIVIDE ( CALCULATE ( COUNTROWS ( Fact_Orders ), Fact_Orders[order_status] = "delivered" ), [Total Customers], 0 )

Customer Lifetime Revenue =
DIVIDE ( CALCULATE ( SUM ( Fact_Orders[item_revenue] ), Fact_Orders[order_status] = "delivered" ), [Total Customers], 0 )

New Customers =
CALCULATE ( DISTINCTCOUNT ( Fact_Orders[customer_unique_id] ), Fact_Orders[order_seq] = 1 )
-- Fact_Orders[order_seq] is created in Power Query (see power_query_import.m): 1 = the customer's first delivered order.

Returning Customer Orders =
CALCULATE ( COUNTROWS ( Fact_Orders ), Fact_Orders[order_seq] > 1 )
```

## Delivery and satisfaction

```dax
Avg Delivery Days = AVERAGE ( Fact_Orders[delivery_days] )

Avg Estimated Days = AVERAGE ( Fact_Orders[estimated_days] )

Late Orders = CALCULATE ( COUNTROWS ( Fact_Orders ), Fact_Orders[is_late] = 1 )

Late Delivery % =
DIVIDE ( [Late Orders], CALCULATE ( COUNTROWS ( Fact_Orders ), NOT ISBLANK ( Fact_Orders[is_late] ) ), 0 )

Avg Freight per Order = AVERAGE ( Fact_Orders[freight_value] )

Avg Review Score = AVERAGE ( Fact_Reviews[review_score] )

Low Rating % =
DIVIDE ( CALCULATE ( COUNTROWS ( Fact_Reviews ), Fact_Reviews[review_score] <= 2 ), COUNTROWS ( Fact_Reviews ), 0 )

Review Count = COUNTROWS ( Fact_Reviews )
```

## Payments

```dax
Payment Value = SUM ( Fact_Payments[payment_value] )

Avg Transaction Value = AVERAGE ( Fact_Payments[payment_value] )

Credit Card Share % =
DIVIDE ( CALCULATE ( [Payment Value], Fact_Payments[payment_type] = "credit_card" ), [Payment Value], 0 )

Avg Instalments =
CALCULATE ( AVERAGE ( Fact_Payments[payment_installments] ), Fact_Payments[payment_type] = "credit_card" )
```

## Modelling notes (avoid the classic traps)

1. **Relate `Dim_Date` only to `Fact_Orders[purchase_date]`.** Items, payments and reviews inherit the date filter through
   `Fact_Orders`. Relating the date table to several facts creates ambiguous paths.
2. Relationships, all one-to-many with single-direction filtering:

| From (1) | To (many) |
|---|---|
| Dim_Date[date_key] | Fact_Orders[purchase_date] |
| Dim_Customer[customer_unique_id] | Fact_Orders[customer_unique_id] |
| Dim_Geography[state] | Fact_Orders[customer_state] |
| Fact_Orders[order_id] | Fact_Order_Items[order_id] |
| Fact_Orders[order_id] | Fact_Payments[order_id] |
| Fact_Orders[order_id] | Fact_Reviews[order_id] |
| Dim_Product[product_id] | Fact_Order_Items[product_id] |
| Dim_Seller[seller_id] | Fact_Order_Items[seller_id] |
| Dim_Customer[customer_unique_id] | RFM_Segments[customer_unique_id] (one-to-one) |

3. Product-category and seller slicers filter `Fact_Order_Items` only. Use the item-based measures (`Total Revenue`,
   `Delivered Orders`) on pages that use those slicers, not `Total Orders`.
4. Never join payments or reviews directly to items: that multiplies rows and inflates revenue.

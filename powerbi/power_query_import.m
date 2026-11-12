// Power Query (M) - import every star-schema CSV from data/processed/powerbi
// 1. Home > Transform data > Manage Parameters > New: name = DataFolder, type = Text,
//    value = full path, e.g.  C:\Projects\ecommerce-intelligence-platform\data\processed\powerbi\
// 2. For each table below: Home > New Source > Blank Query > Advanced Editor > paste the block.

// ---------- Fact_Orders ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "fact_orders.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"purchase_date", type date}, {"purchase_month", type date}, {"purchase_ts", type datetime},
        {"delivered_ts", type datetime}, {"estimated_ts", type datetime},
        {"delivery_days", Int64.Type}, {"estimated_days", Int64.Type}, {"delivery_delay_days", Int64.Type}, {"is_late", Int64.Type},
        {"item_revenue", type number}, {"freight_value", type number}, {"payment_value", type number}, {"avg_review_score", type number},
        {"items_count", Int64.Type}, {"max_installments", Int64.Type}}, "en-US"),
    // Order sequence per customer (1 = first order) used by "New Customers"
    Delivered = Table.SelectRows(Typed, each [order_status] = "delivered"),
    Sorted    = Table.Sort(Delivered, {{"customer_unique_id", Order.Ascending}, {"purchase_ts", Order.Ascending}}),
    Grouped   = Table.Group(Sorted, {"customer_unique_id"}, {{"all", each Table.AddIndexColumn(_, "order_seq", 1, 1), type table}}),
    Expanded  = Table.Combine(Grouped[all]),
    Merged    = Table.NestedJoin(Typed, {"order_id"}, Expanded, {"order_id"}, "seq", JoinKind.LeftOuter),
    Result    = Table.ExpandTableColumn(Merged, "seq", {"order_seq"}, {"order_seq"})
in
    Result

// ---------- Generic loader (use for the other 9 tables; change the file name) ----------
// let
//     Source   = Csv.Document(File.Contents(DataFolder & "fact_order_items.csv"), [Delimiter = ",", Encoding = 65001]),
//     Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
//     Typed    = Table.TransformColumnTypes(Promoted, {{"price", type number}, {"freight_value", type number}, {"purchase_date", type date}}, "en-US")
// in
//     Typed
//
// Files: dim_customer, dim_product, dim_seller, dim_date (date_key -> type date), dim_geography,
//        fact_order_items, fact_payments, fact_reviews (review_date -> date), rfm_segments, cohort_retention, revenue_forecast, churn_scores

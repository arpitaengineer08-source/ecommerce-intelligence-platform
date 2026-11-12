"""
E-Commerce Intelligence Platform - Streamlit front-end.
Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import DATA_PROCESSED, DATABASE_URL, DUCKDB_PATH, STATES
from python.database_loader import Database, load_query_library
from python.scenario import baseline_from_db, run_scenario
from style import C, CSS, callout, kpi_row, money, register_template, style

st.set_page_config(page_title="E-Commerce Intelligence Platform", page_icon="◐", layout="wide")
register_template()
st.markdown(CSS, unsafe_allow_html=True)


def show(fig, key=None):
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except Exception:
        st.plotly_chart(fig, use_container_width=True, key=key)


def table(df, **kw):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def panel(title, sub=""):
    st.markdown(f'<div class="panel-title">{title}</div><div class="panel-sub">{sub}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------------------------------ data layer
def _warehouse_complete() -> bool:
    """Check the DuckDB file in a separate process (avoids file-lock / config clashes with this one)."""
    import subprocess
    code = ("import duckdb,sys;c=duckdb.connect(sys.argv[1],read_only=True);"
            "c.execute('SELECT 1 FROM analytics.rfm_segments LIMIT 1');c.execute('SELECT 1 FROM analytics.recommendations LIMIT 1')")
    try:
        return subprocess.run([sys.executable, "-c", code, str(DUCKDB_PATH)], capture_output=True, timeout=60).returncode == 0
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def get_db() -> Database:
    """Open the warehouse. Rebuild it automatically when it is missing OR only partially built."""
    if not DATABASE_URL:
        ok = DUCKDB_PATH.exists() and (DATA_PROCESSED / "run_manifest.json").exists() and _warehouse_complete()
        if not ok:
            import subprocess
            with st.spinner("Building the warehouse and analytics (about 10-20 seconds)..."):
                r = subprocess.run([sys.executable, str(ROOT / "run_pipeline.py")], capture_output=True, text=True)
            if r.returncode != 0:
                st.error("The pipeline failed. Run `python run_pipeline.py` in a terminal and read the error below.")
                st.code((r.stdout[-1500:] + "\n" + r.stderr[-2500:]).strip())
                st.stop()
    return Database(read_only=True)


def sql(q: str) -> pd.DataFrame:
    return get_db().query(q)


@st.cache_data(show_spinner=False)
def load_all():
    t = {}
    t["orders"] = sql("SELECT * FROM analytics.fact_orders")
    for c in ["purchase_ts", "purchase_date", "purchase_month"]:
        t["orders"][c] = pd.to_datetime(t["orders"][c])
    o = t["orders"]
    d = o[o.order_status == "delivered"].sort_values("purchase_ts")
    seq = d.groupby("customer_unique_id").cumcount() + 1
    t["orders"]["order_seq"] = seq.reindex(o.index)
    t["items"] = sql("""SELECT fi.order_id, fi.order_item_id, fi.product_id, fi.seller_id, fi.customer_state, fi.order_status,
                               fi.purchase_month, fi.price, fi.freight_value, dp.category
                        FROM analytics.fact_order_items fi JOIN analytics.dim_product dp USING (product_id)""")
    t["items"]["purchase_month"] = pd.to_datetime(t["items"]["purchase_month"])
    t["reviews"] = sql("SELECT review_id, order_id, review_score, review_comment_message, review_month FROM analytics.fact_reviews")
    t["reviews"]["review_month"] = pd.to_datetime(t["reviews"]["review_month"])
    t["payments"] = sql("SELECT * FROM analytics.fact_payments")
    for n in ["rfm_segments", "rfm_summary", "cohort_retention", "revenue_forecast", "forecast_metrics", "churn_scores",
              "churn_model_metrics", "churn_coefficients", "scenarios", "recommendations", "data_quality_checks", "cleaning_log", "dim_geography"]:
        t[n] = sql(f"SELECT * FROM analytics.{n}")
    t["revenue_forecast"]["month"] = pd.to_datetime(t["revenue_forecast"]["month"])
    t["manifest"] = json.loads((DATA_PROCESSED / "run_manifest.json").read_text()) if (DATA_PROCESSED / "run_manifest.json").exists() else {}
    return t


T = load_all()
ALL_MONTHS = sorted(T["orders"].purchase_month.dropna().unique())
MONTH_LABELS = [pd.Timestamp(m).strftime("%Y-%m") for m in ALL_MONTHS]
SOURCE = T["manifest"].get("source", "synthetic")

# ------------------------------------------------------------------------------------------ sidebar
PAGES = ["Executive Overview", "Customer Intelligence", "Product & Category", "Orders & Delivery",
         "Revenue & Payments", "Customer Satisfaction", "Predictive & Strategy", "Business Recommendations",
         "SQL Lab", "Data Quality & Architecture"]
with st.sidebar:
    st.markdown('<div class="brand">E-Commerce<br><span>Intelligence Platform</span></div>'
                '<div class="brand-sub">What is happening, why, and what next</div>', unsafe_allow_html=True)
    page = st.radio("Navigate", PAGES, label_visibility="collapsed")
    st.markdown("---")
    st.caption("FILTERS  (apply to every page)")
    lo, hi = st.select_slider("Period", options=MONTH_LABELS, value=(MONTH_LABELS[0], MONTH_LABELS[-1]))
    states = st.multiselect("Customer state", sorted(T["orders"].customer_state.dropna().unique()))
    cats = st.multiselect("Product category", sorted(T["items"].category.dropna().unique()))
    st.markdown("---")
    st.caption(f"Data source: **{SOURCE}**  \nEngine: {T['manifest'].get('engine', 'duckdb')}")
    if SOURCE == "synthetic":
        st.caption("Synthetic Olist-style data. Run `python run_pipeline.py --real` with the Kaggle CSVs for real results.")


def filtered():
    o = T["orders"]; i = T["items"]
    o = o[(o.purchase_month >= pd.Timestamp(lo + "-01")) & (o.purchase_month <= pd.Timestamp(hi + "-01"))]
    if states:
        o = o[o.customer_state.isin(states)]
    i = i[i.order_id.isin(o.order_id)]
    if cats:
        i = i[i.category.isin(cats)]
        o = o[o.order_id.isin(i.order_id)]
    od = o[o.order_status == "delivered"]
    idl = i[i.order_status == "delivered"]
    rv = T["reviews"][T["reviews"].order_id.isin(od.order_id)]
    pay = T["payments"][T["payments"].order_id.isin(od.order_id)]
    return o, od, i, idl, rv, pay


O, OD, I, IDL, RV, PAY = filtered()
if OD.empty:
    st.warning("No delivered orders match these filters. Widen the period or clear a filter.")
    st.stop()
REV = float(IDL.price.sum()); N_ORD = len(OD); AOV = REV / max(N_ORD, 1); N_CUST = OD.customer_unique_id.nunique()


def hero(title, text, chips=()):
    ch = "".join(f'<span class="chip">{c}</span>' for c in chips)
    return f'<div class="hero"><div>{ch}</div><h1>{title}</h1><p>{text}</p>'


monthly = IDL.groupby("purchase_month").agg(revenue=("price", "sum")).join(OD.groupby("purchase_month").size().rename("orders")).reset_index()

# ================================================================================ 1. EXECUTIVE
if page == PAGES[0]:
    growth = None
    if len(monthly) >= 2:
        growth = (monthly.revenue.iloc[-1] / monthly.revenue.iloc[-2] - 1) * 100
    repeat = (OD.groupby("customer_unique_id").size() > 1).mean() * 100
    cancel = (O.order_status.isin(["canceled", "unavailable"])).mean() * 100
    top_cat = IDL.groupby("category").price.sum().sort_values(ascending=False)
    rec_top = T["recommendations"].iloc[0] if len(T["recommendations"]) else None
    late_rev = RV.merge(OD[["order_id", "is_late"]], on="order_id")
    gap = late_rev[late_rev.is_late == 0].review_score.mean() - late_rev[late_rev.is_late == 1].review_score.mean()
    story = (f'<div class="story"><div class="s1"><b>What is happening</b><span>{money(REV)} revenue from {N_ORD:,} delivered orders. '
             f'{top_cat.index[0].replace("_", " ").title()} leads with {top_cat.iloc[0] / REV * 100:.0f}% of sales. '
             f'Only {repeat:.1f}% of customers buy twice.</span></div>'
             f'<div class="s2"><b>Why it is happening</b><span>Late deliveries cost {gap:.1f} review stars on average, and new-customer '
             f'acquisition drives nearly all growth.</span></div>'
             f'<div class="s3"><b>What to do next</b><span>{rec_top.action if rec_top is not None else "Run the pipeline to generate recommendations."}</span></div></div></div>')
    st.markdown(hero("What is happening in the business, why, and what should we do next?",
                     "Live view of revenue, customers, delivery and satisfaction. Every number responds to the filters on the left.",
                     [f"{lo} to {hi}", f"{len(states) or 'all'} states" if states else "all states", f"{len(cats) or 'all'} categories" if cats else "all categories"]) + story,
                unsafe_allow_html=True)
    st.markdown(kpi_row([
        ("Revenue", money(REV), "delivered orders, item price", C["iris"]),
        ("Delivered orders", f"{N_ORD:,}", f"{cancel:.1f}% cancelled or unavailable", C["cyan"]),
        ("Average order value", f"R${AOV:,.0f}", "revenue / delivered orders", C["amber"]),
        ("Unique customers", f"{N_CUST:,}", f"{repeat:.1f}% repeat", C["mint"]),
        ("Monthly growth", f"{growth:+.1f}%" if growth is not None else "n/a", "latest month vs previous", C["rose"], "up" if (growth or 0) >= 0 else "down"),
        ("Avg review", f"{RV.review_score.mean():.2f} / 5", f"{OD.is_late.mean() * 100:.1f}% late deliveries", C["iris"]),
    ]), unsafe_allow_html=True)

    c1, c2 = st.columns([1.65, 1])
    with c1:
        panel("Revenue and orders by month", "Bars: revenue. Line: delivered orders.")
        fig = go.Figure()
        fig.add_bar(x=monthly.purchase_month, y=monthly.revenue, name="Revenue", marker_color=C["iris"], opacity=0.9)
        fig.add_scatter(x=monthly.purchase_month, y=monthly.orders, name="Orders", yaxis="y2", line=dict(color=C["cyan"], width=3))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False), yaxis_title="R$")
        show(style(fig, 360))
    with c2:
        panel("Order status mix", "Share of all orders in the period")
        s = O.order_status.value_counts().reset_index(); s.columns = ["status", "orders"]
        fig = px.pie(s, names="status", values="orders", hole=0.62, color_discrete_sequence=[C["mint"], C["iris"], C["rose"], C["amber"], C["cyan"], "#B39DFF", "#7BE0F2", "#FFD28A"])
        fig.update_traces(textinfo="none", sort=False); fig.update_layout(legend=dict(orientation="v", y=0.5, x=1.0))
        show(style(fig, 360))
    c3, c4 = st.columns([1.2, 1])
    with c3:
        panel("Where customers buy", "Bubble size = revenue by customer state")
        g = T["dim_geography"]; r = OD.groupby("customer_state").item_revenue.sum().rename("revenue").reset_index().merge(g, left_on="customer_state", right_on="state")
        fig = px.scatter_geo(r, lat="lat", lon="lon", size="revenue", color="region", hover_name="state", hover_data={"revenue": ":,.0f", "lat": False, "lon": False},
                             size_max=46, color_discrete_sequence=[C["iris"], C["cyan"], C["amber"], C["mint"], C["rose"]])
        fig.update_geos(scope="south america", showcountries=True, countrycolor=C["edge"], landcolor="#12152e", showocean=True, oceancolor="#0c0e1f",
                        bgcolor="rgba(0,0,0,0)", lataxis_range=[-35, 6], lonaxis_range=[-75, -33], showland=True, coastlinecolor=C["edge"])
        show(style(fig, 400))
    with c4:
        panel("Revenue by category", "Top 12 categories")
        cc = top_cat.head(12).reset_index(); cc.columns = ["category", "revenue"]
        fig = px.bar(cc[::-1], x="revenue", y="category", orientation="h", color="revenue", color_continuous_scale=[C["edge"], C["iris"], C["cyan"]])
        fig.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="")
        show(style(fig, 400))
    st.markdown(callout(f"<b>So what?</b> The top 3 categories earn {top_cat.head(3).sum() / REV * 100:.0f}% of revenue and {cancel:.1f}% of orders never reach delivery. "
                        "Protect the leading categories' availability and delivery SLAs before chasing new ones."), unsafe_allow_html=True)

# ================================================================================ 2. CUSTOMERS
elif page == PAGES[1]:
    st.markdown(hero("Who are the customers, and who is worth keeping?", "RFM segments, cohort retention and value concentration.", ["RFM", "Cohorts", "CLV"]) + "</div>", unsafe_allow_html=True)
    new_c = int((OD.order_seq == 1).sum()); ret_c = int((OD.order_seq > 1).sum())
    cust = OD.groupby("customer_unique_id").agg(n=("order_id", "count"), rev=("item_revenue", "sum"))
    st.markdown(kpi_row([("New customers", f"{new_c:,}", "first orders in period", C["mint"]),
                         ("Returning-customer orders", f"{ret_c:,}", f"{ret_c / max(N_ORD, 1) * 100:.1f}% of orders", C["cyan"]),
                         ("Avg lifetime revenue", f"R${cust.rev.mean():,.0f}", "per customer, in period", C["amber"]),
                         ("Avg purchase frequency", f"{cust.n.mean():.2f}", "orders per customer", C["iris"]),
                         ("Top 10% customers", f"{cust.rev.nlargest(max(len(cust) // 10, 1)).sum() / cust.rev.sum() * 100:.0f}%", "share of revenue", C["rose"])]), unsafe_allow_html=True)
    rs = T["rfm_summary"]
    c1, c2 = st.columns([1.1, 1])
    with c1:
        panel("RFM segments", "Customers vs. revenue share (whole history, not filtered)")
        fig = go.Figure()
        fig.add_bar(y=rs.segment, x=rs.customer_share_pct, orientation="h", name="% of customers", marker_color=C["cyan"])
        fig.add_bar(y=rs.segment, x=rs.revenue_share_pct, orientation="h", name="% of revenue", marker_color=C["iris"])
        fig.update_layout(barmode="group", yaxis=dict(autorange="reversed"), xaxis_title="%")
        show(style(fig, 400))
    with c2:
        panel("Segment playbook", "What to do with each group")
        from python.rfm_segmentation import SEGMENT_ACTIONS
        pb = rs[["segment", "customers", "revenue_share_pct"]].copy(); pb["action"] = pb.segment.map(SEGMENT_ACTIONS)
        pb["revenue_share_pct"] = pb.revenue_share_pct.round(1)
        table(pb, height=330)
    panel("Cohort retention", "% of each first-purchase cohort that bought again N months later")
    co = T["cohort_retention"]; mat = co[co.month_index.between(1, 12)].pivot(index="cohort_month", columns="month_index", values="retention_pct")
    fig = px.imshow(mat, text_auto=".1f", aspect="auto", color_continuous_scale=[[0, "#12152e"], [0.4, C["iris"]], [1, C["amber"]]], labels=dict(x="Months since first order", y="Cohort", color="%"))
    show(style(fig, 460))
    c3, c4 = st.columns(2)
    with c3:
        panel("Most valuable customers", "Lifetime revenue in period")
        top = OD.groupby(["customer_unique_id", "customer_state"]).agg(orders=("order_id", "count"), revenue=("item_revenue", "sum")).reset_index().nlargest(15, "revenue")
        top["customer_unique_id"] = top.customer_unique_id.str[:10] + "…"; top["revenue"] = top.revenue.round(0)
        table(top, height=420)
    with c4:
        panel("Customers by state", "Customers and revenue per customer")
        g = OD.groupby("customer_state").agg(customers=("customer_unique_id", "nunique"), revenue=("item_revenue", "sum")).reset_index()
        g["rev_per_customer"] = g.revenue / g.customers
        fig = px.scatter(g, x="customers", y="rev_per_customer", size="revenue", hover_name="customer_state", text="customer_state", log_x=True, color_discrete_sequence=[C["cyan"]])
        fig.update_traces(textposition="top center"); fig.update_layout(yaxis_title="Revenue per customer (R$)")
        show(style(fig, 420))
    st.markdown(callout("<b>So what?</b> Repeat buying is rare, so a small lift in second-order rate has outsized impact. Focus first on 'Potential Loyalists' and 'At Risk' - they hold the largest revenue share outside Champions.", C["mint"]), unsafe_allow_html=True)

# ================================================================================ 3. PRODUCTS
elif page == PAGES[2]:
    st.markdown(hero("What sells, what does not, and why?", "Product and category performance, growth and concentration.", ["Pareto", "Growth", "Mix"]) + "</div>", unsafe_allow_html=True)
    pc = IDL.groupby("category").agg(revenue=("price", "sum"), units=("price", "size"), asp=("price", "mean")).reset_index().sort_values("revenue", ascending=False)
    pc["share"] = pc.revenue / pc.revenue.sum() * 100; pc["cum"] = pc.share.cumsum()
    st.markdown(kpi_row([("Units sold", f"{len(IDL):,}", "delivered items", C["cyan"]), ("Categories", f"{len(pc)}", "with sales", C["iris"]),
                         ("Average selling price", f"R${IDL.price.mean():,.0f}", "per item", C["amber"]),
                         ("Top category share", f"{pc.share.iloc[0]:.1f}%", pc.category.iloc[0], C["mint"]),
                         ("Products sold", f"{IDL.product_id.nunique():,}", "distinct", C["rose"])]), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        panel("Pareto: category revenue and cumulative share")
        fig = go.Figure(); fig.add_bar(x=pc.category, y=pc.revenue, marker_color=C["iris"], name="Revenue")
        fig.add_scatter(x=pc.category, y=pc.cum, yaxis="y2", name="Cumulative %", line=dict(color=C["amber"], width=3))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105], showgrid=False), xaxis_tickangle=-45)
        show(style(fig, 420))
    with c2:
        panel("Category treemap", "Area = revenue, colour = average selling price")
        fig = px.treemap(pc, path=["category"], values="revenue", color="asp", color_continuous_scale=[C["cyan"], C["iris"], C["rose"]])
        fig.update_traces(marker_line_color=C["bg"], marker_line_width=2)
        show(style(fig, 420))
    c3, c4 = st.columns(2)
    prod = IDL.groupby(["product_id", "category"]).agg(revenue=("price", "sum"), units=("price", "size")).reset_index()
    with c3:
        panel("Top 10 products", "By revenue")
        t = prod.nlargest(10, "revenue"); t["product_id"] = t.product_id.str[:10] + "…"; t["revenue"] = t.revenue.round(0); table(t, height=390)
    with c4:
        panel("Bottom 10 products", "Lowest revenue among products with 3+ units")
        b = prod[prod.units >= 3].nsmallest(10, "revenue"); b["product_id"] = b.product_id.str[:10] + "…"; b["revenue"] = b.revenue.round(0); table(b, height=390)
    panel("Category trends", "Monthly revenue of the selected categories")
    pick = st.multiselect("Categories to compare", pc.category.tolist(), default=pc.category.head(5).tolist(), key="trend_cats")
    tr = IDL[IDL.category.isin(pick)].groupby(["purchase_month", "category"]).price.sum().reset_index()
    show(style(px.line(tr, x="purchase_month", y="price", color="category", markers=True), 380))
    h = IDL.copy(); h["yr"] = h.purchase_month.dt.year
    g = h[h.purchase_month.dt.month <= 8].pivot_table(index="category", columns="yr", values="price", aggfunc="sum")
    if {2017, 2018} <= set(g.columns):
        g["growth_pct"] = (g[2018] / g[2017] - 1) * 100; g = g.dropna().sort_values("growth_pct")
        panel("Category growth, Jan-Aug 2018 vs Jan-Aug 2017")
        fig = px.bar(g.reset_index(), x="growth_pct", y="category", orientation="h", color="growth_pct", color_continuous_scale=[C["rose"], C["edge"], C["mint"]], color_continuous_midpoint=0)
        fig.update_layout(coloraxis_showscale=False, xaxis_title="Growth %", yaxis_title="")
        show(style(fig, 520))
        losers = g[g.growth_pct < 0].head(3).index.tolist()
        st.markdown(callout(f"<b>So what?</b> Categories shrinking year on year: <b>{', '.join(losers) or 'none'}</b>. Check pricing, availability and reviews before adding promotional spend.", C["rose"]), unsafe_allow_html=True)

# ================================================================================ 4. DELIVERY
elif page == PAGES[3]:
    st.markdown(hero("How well do we deliver on our promise?", "Estimated vs actual delivery, late rates, sellers and freight.", ["SLA", "Sellers", "Freight"]) + "</div>", unsafe_allow_html=True)
    dd = OD.dropna(subset=["delivered_ts"])
    st.markdown(kpi_row([("Avg delivery time", f"{dd.delivery_days.mean():.1f} days", f"estimated {dd.estimated_days.mean():.1f} days", C["cyan"]),
                         ("Late deliveries", f"{dd.is_late.mean() * 100:.1f}%", "after estimated date", C["rose"], "down"),
                         ("Cancelled / unavailable", f"{O.order_status.isin(['canceled', 'unavailable']).mean() * 100:.1f}%", "of all orders", C["amber"]),
                         ("Avg freight per order", f"R${OD.freight_value.mean():,.1f}", f"{OD.freight_value.sum() / max(OD.item_revenue.sum(), 1) * 100:.0f}% of item value", C["iris"])]), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        panel("Estimated vs actual delivery days by state", "States with 50+ orders")
        g = dd.groupby("customer_state").agg(actual=("delivery_days", "mean"), estimated=("estimated_days", "mean"), n=("order_id", "count")).reset_index()
        g = g[g.n >= 50].sort_values("actual", ascending=False).head(20)
        fig = go.Figure(); fig.add_bar(x=g.customer_state, y=g.estimated, name="Estimated", marker_color=C["edge"])
        fig.add_bar(x=g.customer_state, y=g.actual, name="Actual", marker_color=C["cyan"]); fig.update_layout(barmode="group", yaxis_title="days")
        show(style(fig, 380))
    with c2:
        panel("Delivery performance trend", "Late % and average delivery days by purchase month")
        m = dd.groupby("purchase_month").agg(late=("is_late", "mean"), days=("delivery_days", "mean")).reset_index()
        fig = go.Figure(); fig.add_scatter(x=m.purchase_month, y=m.late * 100, name="Late %", fill="tozeroy", line=dict(color=C["rose"], width=3), fillcolor="rgba(255,92,138,0.15)")
        fig.add_scatter(x=m.purchase_month, y=m.days, name="Avg days", yaxis="y2", line=dict(color=C["cyan"], width=3))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False), yaxis_title="Late %")
        show(style(fig, 380))
    c3, c4 = st.columns(2)
    with c3:
        panel("Regional delivery gap")
        r = dd.merge(T["dim_geography"], left_on="customer_state", right_on="state").groupby("region").agg(days=("delivery_days", "mean"), late=("is_late", "mean"), freight=("freight_value", "mean")).reset_index().sort_values("days")
        fig = px.bar(r, x="region", y="days", color="late", color_continuous_scale=[C["mint"], C["amber"], C["rose"]], text=r.days.round(1)); fig.update_layout(coloraxis_colorbar_title="Late %", xaxis_title="")
        show(style(fig, 360))
    with c4:
        panel("Seller reliability", "Each bubble is a seller with 15+ orders; top-right is the problem zone")
        so = I[["order_id", "seller_id"]].drop_duplicates().merge(dd[["order_id", "is_late", "avg_review_score", "delivery_days"]], on="order_id")
        sr = so.groupby("seller_id").agg(orders=("order_id", "count"), late=("is_late", "mean"), review=("avg_review_score", "mean")).reset_index()
        sr = sr[sr.orders >= 15].merge(IDL.groupby("seller_id").price.sum().rename("revenue").reset_index(), on="seller_id"); sr["late_pct"] = sr.late * 100
        if len(sr):
            fig = px.scatter(sr, x="orders", y="late_pct", size="revenue", color="review", color_continuous_scale=[C["rose"], C["amber"], C["mint"]], hover_name="seller_id")
            fig.update_layout(yaxis_title="Late %", coloraxis_colorbar_title="Avg review"); show(style(fig, 360))
        else:
            st.info("Not enough orders per seller under these filters.")
    panel("Freight as % of item price by category")
    fr = IDL.groupby("category").agg(freight=("freight_value", "sum"), price=("price", "sum"), n=("price", "size")).reset_index(); fr = fr[fr.n >= 50]; fr["pct"] = fr.freight / fr.price * 100
    show(style(px.bar(fr.sort_values("pct", ascending=False), x="category", y="pct", color="pct", color_continuous_scale=[C["cyan"], C["iris"], C["rose"]]).update_layout(coloraxis_showscale=False, xaxis_tickangle=-45, yaxis_title="%"), 360))
    st.markdown(callout("<b>So what?</b> Slow regions get both longer delivery and higher freight. Add buffer to their delivery estimates, and review carriers or hubs there.", C["cyan"]), unsafe_allow_html=True)

# ================================================================================ 5. PAYMENTS
elif page == PAGES[4]:
    st.markdown(hero("How do customers pay, and what does shipping add?", "Payment methods, instalments, freight and cancellation impact.", ["Payments", "Instalments"]) + "</div>", unsafe_allow_html=True)
    cc = PAY[PAY.payment_type == "credit_card"]
    lost = O[O.order_status.isin(["canceled", "unavailable"])].item_revenue.sum()
    st.markdown(kpi_row([("Payment value", money(PAY.payment_value.sum()), "items + freight", C["iris"]),
                         ("Avg transaction", f"R${PAY.payment_value.mean():,.0f}", "per payment record", C["cyan"]),
                         ("Credit-card share", f"{cc.payment_value.sum() / PAY.payment_value.sum() * 100:.0f}%", "of payment value", C["amber"]),
                         ("Avg instalments", f"{cc.payment_installments.mean():.1f}", "credit-card payments", C["mint"]),
                         ("Revenue lost to failed orders", money(lost), "cancelled + unavailable", C["rose"])]), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        panel("Payment value by method")
        m = PAY.groupby("payment_type").agg(value=("payment_value", "sum"), avg=("payment_value", "mean"), n=("payment_value", "size")).reset_index()
        show(style(px.pie(m, names="payment_type", values="value", hole=0.6), 340))
    with c2:
        panel("Instalment distribution", "Credit-card payments; colour = average payment value")
        ins = cc.groupby("payment_installments").agg(n=("payment_value", "size"), avg=("payment_value", "mean")).reset_index()
        show(style(px.bar(ins, x="payment_installments", y="n", color="avg", color_continuous_scale=[C["cyan"], C["iris"], C["rose"]]).update_layout(coloraxis_colorbar_title="Avg R$"), 340))
    c3, c4 = st.columns(2)
    with c3:
        panel("Freight contribution over time")
        f = OD.groupby("purchase_month").agg(items=("item_revenue", "sum"), freight=("freight_value", "sum")).reset_index()
        fig = go.Figure(); fig.add_bar(x=f.purchase_month, y=f["items"], name="Items", marker_color=C["iris"]); fig.add_bar(x=f.purchase_month, y=f.freight, name="Freight", marker_color=C["amber"]); fig.update_layout(barmode="stack")
        show(style(fig, 340))
    with c4:
        panel("Cancellation impact by month")
        cm = O.assign(failed=O.order_status.isin(["canceled", "unavailable"])).groupby("purchase_month").agg(rate=("failed", "mean"), lost=("item_revenue", lambda s: s[O.loc[s.index, "order_status"].isin(["canceled", "unavailable"])].sum())).reset_index()
        fig = go.Figure(); fig.add_bar(x=cm.purchase_month, y=cm.lost, name="Lost revenue", marker_color=C["rose"]); fig.add_scatter(x=cm.purchase_month, y=cm.rate * 100, name="Rate %", yaxis="y2", line=dict(color=C["amber"], width=3))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False)); show(style(fig, 340))
    panel("Payment behaviour by customer segment", "Average instalments and credit-card share per RFM segment")
    seg = T["rfm_segments"][["customer_unique_id", "segment"]]
    j = OD[["order_id", "customer_unique_id", "max_installments"]].merge(seg, on="customer_unique_id").merge(PAY[["order_id", "payment_type", "payment_value"]], on="order_id")
    sg = j.groupby("segment").agg(avg_installments=("max_installments", "mean"), cc_share=("payment_type", lambda s: (s == "credit_card").mean() * 100), avg_payment=("payment_value", "mean")).round(2).reset_index()
    table(sg)

# ================================================================================ 6. SATISFACTION
elif page == PAGES[5]:
    st.markdown(hero("Why are customers happy or unhappy?", "Ratings, delivery experience and complaint themes.", ["Reviews", "Delivery vs rating"]) + "</div>", unsafe_allow_html=True)
    low = (RV.review_score <= 2).mean() * 100
    st.markdown(kpi_row([("Average review", f"{RV.review_score.mean():.2f} / 5", f"{len(RV):,} reviews", C["amber"]), ("Low ratings (1-2)", f"{low:.1f}%", "of reviews", C["rose"], "down"),
                         ("5-star share", f"{(RV.review_score == 5).mean() * 100:.0f}%", "of reviews", C["mint"]), ("Reviews with comments", f"{RV.review_comment_message.notna().mean() * 100:.0f}%", "wrote text", C["cyan"])]), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        panel("Rating distribution")
        d = RV.review_score.value_counts().sort_index().reset_index(); d.columns = ["score", "reviews"]
        show(style(px.bar(d, x="score", y="reviews", color="score", color_continuous_scale=[C["rose"], C["amber"], C["mint"]]).update_layout(coloraxis_showscale=False), 340))
    with c2:
        panel("Delivery vs estimate and the rating", "Delivery delay is the strongest signal in the data")
        x = OD.dropna(subset=["delivery_delay_days", "avg_review_score"]).copy()
        x["bucket"] = pd.cut(x.delivery_delay_days, [-999, -10, -1, 0, 5, 999], labels=["10+ days early", "1-9 days early", "on estimate day", "1-5 days late", "6+ days late"])
        b = x.groupby("bucket", observed=True).agg(score=("avg_review_score", "mean"), n=("order_id", "count")).reset_index()
        show(style(px.bar(b, x="bucket", y="score", color="score", color_continuous_scale=[C["rose"], C["amber"], C["mint"]], text=b.score.round(2)).update_layout(coloraxis_showscale=False, yaxis_range=[0, 5], xaxis_title=""), 340))
    c3, c4 = st.columns(2)
    with c3:
        panel("Rating trend", "Average score by month")
        t = RV.groupby("review_month").review_score.mean().reset_index()
        show(style(px.line(t, x="review_month", y="review_score", markers=True).update_layout(yaxis_range=[1, 5]), 340))
    with c4:
        panel("Lowest-rated categories", "100+ reviews")
        rc = RV.merge(I[["order_id", "category"]].drop_duplicates(), on="order_id").groupby("category").review_score.agg(["mean", "size"]).reset_index(); rc = rc[rc["size"] >= 100].sort_values("mean").head(10)
        show(style(px.bar(rc, x="mean", y="category", orientation="h", color="mean", color_continuous_scale=[C["rose"], C["amber"], C["mint"]]).update_layout(coloraxis_showscale=False, xaxis_range=[1, 5], yaxis_title="", xaxis_title="avg score"), 340))
    panel("What unhappy customers say", "Keyword themes in 1-2 star comments (Portuguese and English keywords)")
    lows = RV[(RV.review_score <= 2) & RV.review_comment_message.notna()].review_comment_message.str.lower()
    rules = {"Late / missing delivery": ["atras", "demor", "nao recebi", "não recebi", "late"], "Damaged / defective": ["quebrad", "defeito", "damaged"],
             "Quality / not as described": ["qualidade", "diferente", "quality"], "Seller service / missing item": ["vendedor", "respond", "faltou"]}
    def theme(s):
        for k, v in rules.items():
            if any(w in s for w in v): return k
        return "Other"
    if len(lows):
        th = lows.map(theme).value_counts().reset_index(); th.columns = ["theme", "comments"]
        show(style(px.bar(th, x="comments", y="theme", orientation="h", color_discrete_sequence=[C["rose"]]).update_layout(yaxis=dict(autorange="reversed"), yaxis_title=""), 300))
    st.markdown(callout("<b>So what?</b> Low ratings cluster around late deliveries rather than product categories. Improving on-time delivery is the cheapest route to better reviews.", C["amber"]), unsafe_allow_html=True)

# ================================================================================ 7. PREDICTIVE
elif page == PAGES[6]:
    st.markdown(hero("What happens next, and what if we act?", "Forecast with honest baselines, churn-risk identification and a what-if simulator.", ["Forecast", "Churn", "Scenarios"]) + "</div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Revenue forecast", "Churn risk", "Scenario simulator"])
    with tab1:
        fc = T["revenue_forecast"]; fm = T["forecast_metrics"]; best = fm.iloc[0]
        st.markdown(kpi_row([("Best model", best.model, "lowest hold-out RMSE", C["iris"]), ("MAPE", f"{best.MAPE:.1f}%", "hold-out, last 4 months", C["mint"]),
                             ("MAE", money(best.MAE), "per month", C["cyan"]), ("Next 3 months", money(fc[fc.kind == 'future'].forecast.head(3).sum()), "expected revenue", C["amber"])]), unsafe_allow_html=True)
        a = fc[fc.kind == "actual"]; h = fc[fc.kind == "holdout"]; f = fc[fc.kind == "future"]
        fig = go.Figure()
        fig.add_scatter(x=f.month, y=f.upper, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip")
        fig.add_scatter(x=f.month, y=f.lower, mode="lines", fill="tonexty", fillcolor="rgba(52,229,161,0.18)", line=dict(width=0), name="~80% interval")
        fig.add_scatter(x=a.month, y=a.actual, name="Actual", line=dict(color=C["iris"], width=3))
        fig.add_scatter(x=h.month, y=h.forecast, name="Hold-out forecast", line=dict(color=C["amber"], dash="dash", width=2))
        fig.add_scatter(x=f.month, y=f.forecast, name="Forecast", line=dict(color=C["mint"], width=3), mode="lines+markers")
        fig.update_layout(yaxis_title="Monthly revenue (R$)"); show(style(fig, 420))
        panel("Model comparison on hold-out months", "A forecast is only meaningful relative to simple baselines")
        fm2 = fm.copy(); fm2[["MAE", "RMSE"]] = fm2[["MAE", "RMSE"]].round(0); fm2["MAPE"] = fm2.MAPE.round(1); table(fm2)
        from python.forecasting import LIMITATIONS
        st.markdown(callout(f"<b>Limitations.</b> {LIMITATIONS}", C["amber"]), unsafe_allow_html=True)
    with tab2:
        ch = T["churn_scores"]; cm = T["churn_model_metrics"].iloc[0]
        rsum = ch.groupby("risk_segment").agg(customers=("customer_unique_id", "count"), historical_spend=("monetary", "sum")).reset_index()
        hv = ch[ch.risk_segment == "High-value at risk"]
        st.markdown(kpi_row([("High-value at risk", f"{len(hv):,}", f"{money(hv.monetary.sum())} historical spend", C["rose"]), ("Lapsed (180+ days)", f"{(ch.inactivity_status == 'Lapsed').sum():,}", "no purchase in 6 months", C["amber"]),
                             ("Model ROC-AUC", f"{cm.roc_auc:.2f}", f"predicting a purchase within {int(cm.window_days)} days", C["iris"]), ("Base repurchase rate", f"{cm.positive_rate_pct:.1f}%", "in the training sample", C["cyan"])]), unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1.3])
        with c1:
            panel("Customers by risk segment")
            show(style(px.pie(rsum, names="risk_segment", values="customers", hole=0.6, color_discrete_sequence=[C["rose"], C["amber"], C["edge"], C["mint"]]), 340))
        with c2:
            panel("Priority win-back list", "High-value customers who are cooling off")
            pr = hv.sort_values("expected_value_next_window", ascending=False).head(15)[["customer_unique_id", "customer_state", "recency_days", "frequency", "monetary", "repurchase_prob", "retention_action"]].copy()
            pr["customer_unique_id"] = pr.customer_unique_id.str[:10] + "…"; pr["monetary"] = pr.monetary.round(0); pr["repurchase_prob"] = (pr.repurchase_prob * 100).round(1)
            table(pr, height=340)
        weak = cm.roc_auc < 0.6
        st.markdown(callout("<b>Model honesty.</b> " + (f"ROC-AUC is only {cm.roc_auc:.2f}: repurchase is hard to predict from this data (about {cm.positive_rate_pct:.1f}% of customers return), so the model adds little over the inactivity rule. "
                            "Use the rule-based risk segments for campaigns and treat probabilities as weak signals." if weak else f"ROC-AUC {cm.roc_auc:.2f} on a stratified hold-out set."), C["amber"]), unsafe_allow_html=True)
    with tab3:
        base = baseline_from_db(get_db())
        st.markdown("Move the sliders to test a what-if. Assumptions are listed below the chart.")
        a1, a2, a3 = st.columns(3)
        aov_up = a1.slider("Average order value change (%)", -10.0, 20.0, 5.0, 0.5)
        can_dn = a2.slider("Cancellation rate reduction (pp)", 0.0, 1.2, 0.5, 0.1)
        rep_up = a3.slider("Repeat purchases increase (%)", 0.0, 100.0, 10.0, 5.0)
        res = run_scenario(base, aov_up, can_dn, rep_up)
        st.markdown(kpi_row([("Baseline revenue", money(base["revenue"]), "delivered orders", C["cyan"]), ("Scenario revenue", money(res["revenue"]), f"{res['delta_pct']:+.1f}%", C["mint"], "up" if res["delta"] >= 0 else "down"),
                             ("Uplift", money(res["delta"]), "vs baseline", C["amber"])]), unsafe_allow_html=True)
        fig = go.Figure(go.Waterfall(x=["Baseline", "AOV change", "Fewer cancellations", "More repeat orders", "Scenario"], measure=["absolute", "relative", "relative", "relative", "total"],
                                     y=[base["revenue"], res["from_aov"], res["from_cancel"], res["from_repeat"], 0], connector=dict(line=dict(color=C["edge"])),
                                     increasing=dict(marker=dict(color=C["mint"])), decreasing=dict(marker=dict(color=C["rose"])), totals=dict(marker=dict(color=C["iris"]))))
        show(style(fig, 380))
        st.markdown(callout("<b>Assumptions.</b> Fewer cancellations convert into delivered orders at today's AOV. Repeat uplift scales orders beyond each customer's first. AOV change applies to all orders with no volume loss. "
                            "These are planning estimates, not forecasts.", C["iris"]), unsafe_allow_html=True)

# ================================================================================ 8. RECOMMENDATIONS
elif page == PAGES[7]:
    st.markdown(hero("Business recommendations", "Each recommendation follows the same path: what the data shows, why it matters, what to do.", ["Insight", "Impact", "Action"]) + "</div>", unsafe_allow_html=True)
    rec = T["recommendations"]; order = {"High": 0, "Medium": 1, "Low": 2}; col = {"High": C["rose"], "Medium": C["amber"], "Low": C["cyan"]}
    for r in sorted(rec.itertuples(), key=lambda x: order[x.priority]):
        st.markdown(f'<div class="rec" style="--accent:{col[r.priority]}"><span class="tag">{r.priority} priority · {r.module}</span><h4>{r.title}</h4>'
                    f'<p><b>What the data shows.</b> {r.insight}</p><p><b>Why it matters.</b> {r.why}</p><p><b>Recommended action.</b> {r.action}</p></div>', unsafe_allow_html=True)
    st.markdown(callout("<b>Not answerable with this dataset:</b> profit and margin (no cost data), stock-out risk (no inventory data), conversion and cart abandonment (no web events).", C["muted"]), unsafe_allow_html=True)

# ================================================================================ 9. SQL LAB
elif page == PAGES[8]:
    lib = load_query_library()
    st.markdown(hero("SQL Lab", f"{len(lib)} documented analytical queries ({int((lib.level == 'advanced').sum())} advanced: CTEs, window functions, LAG/LEAD, NTILE, FILTER, percentiles). Pick one and run it live.", ["CTEs", "Window functions", "Views"]) + "</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2.2])
    with c1:
        mod = st.selectbox("Module", ["all"] + sorted(lib.module.unique())); lvl = st.radio("Level", ["all", "basic", "advanced"], horizontal=True)
        sub = lib if mod == "all" else lib[lib.module == mod]
        sub = sub if lvl == "all" else sub[sub.level == lvl]
        name = st.selectbox("Query", sub.name.tolist(), format_func=lambda n: f"{n}  -  {sub[sub.name == n].title.iloc[0]}")
    row = lib[lib.name == name].iloc[0]
    with c2:
        st.markdown(f"**Business question:** {row.question}  \n`{row.level}` · module `{row.module}`")
        sql_text = st.text_area("SQL (editable)", row.sql, height=300)
    if st.button("Run query", type="primary"):
        try:
            res = sql(sql_text); st.success(f"{len(res):,} rows"); table(res.head(500))
            st.download_button("Download CSV", res.to_csv(index=False), f"{name}.csv", "text/csv")
        except Exception as e:
            st.error(f"Query failed: {e}")

# ================================================================================ 10. DATA QUALITY & ARCH
else:
    st.markdown(hero("Data quality and architecture", "How the data flows from raw CSV to decisions, and how it is validated.", ["Star schema", "Validation"]) + "</div>", unsafe_allow_html=True)
    st.markdown('<div class="flow"><div class="node"><b>Olist CSVs</b><span>9 source files</span></div><div class="arrow">→</div>'
                '<div class="node"><b>Python ETL</b><span>ingest · clean · validate</span></div><div class="arrow">→</div>'
                '<div class="node"><b>SQL warehouse</b><span>raw · staging · analytics star schema</span></div><div class="arrow">→</div>'
                '<div class="node"><b>Analytics layer</b><span>RFM · cohorts · forecast · churn</span></div><div class="arrow">→</div>'
                '<div class="node"><b>BI + app</b><span>Power BI · Streamlit · reports</span></div></div>', unsafe_allow_html=True)
    dq = T["data_quality_checks"]
    st.markdown(kpi_row([("Checks passed", f"{(dq.status == 'PASS').sum()} / {len(dq)}", "validation suite", C["mint"]), ("Warnings", f"{(dq.status == 'WARN').sum()}", "review recommended", C["amber"]),
                         ("Failures", f"{(dq.status == 'FAIL').sum()}", "blocking issues", C["rose"]), ("Orders processed", f"{T['manifest'].get('orders', 0):,}", "delivered", C["cyan"])]), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        panel("Validation checks"); table(dq, height=460)
    with c2:
        panel("Cleaning actions applied"); cl = T["cleaning_log"]; table(cl[cl.rows_affected > 0], height=460)
    st.markdown(callout("<b>Star schema grain.</b> fact_orders (1 row per order) · fact_order_items (per item) · fact_payments (per payment) · fact_reviews (per review). Keeping grains separate prevents joins from multiplying rows and inflating revenue.", C["iris"]), unsafe_allow_html=True)
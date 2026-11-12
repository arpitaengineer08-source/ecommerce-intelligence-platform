"""What-if business scenario analysis with explicit, editable assumptions."""
from __future__ import annotations
import pandas as pd


def baseline_from_db(db) -> dict:
    d = db.query("""SELECT
        (SELECT COUNT(*) FROM analytics.vw_delivered_orders) AS delivered_orders,
        (SELECT SUM(item_revenue) FROM analytics.vw_delivered_orders) AS revenue,
        (SELECT COUNT(*) FROM analytics.fact_orders) AS total_orders,
        (SELECT COUNT(*) FROM analytics.fact_orders WHERE order_status IN ('canceled','unavailable')) AS failed_orders,
        (SELECT COUNT(DISTINCT customer_unique_id) FROM analytics.vw_delivered_orders) AS customers""").iloc[0]
    delivered, customers = float(d.delivered_orders), float(d.customers)
    return {"delivered_orders": delivered, "revenue": float(d.revenue), "aov": float(d.revenue) / delivered,
            "total_orders": float(d.total_orders), "cancel_rate": float(d.failed_orders) / float(d.total_orders),
            "repeat_orders": delivered - customers}   # orders beyond each customer's first


def run_scenario(base: dict, aov_uplift_pct=0.0, cancel_reduction_pp=0.0, repeat_uplift_pct=0.0) -> dict:
    """
    Assumptions (stated openly):
      * Reduced cancellations convert failed orders into delivered orders at the current AOV.
      * Repeat uplift scales orders placed beyond a customer's first order; AOV unchanged for those.
      * AOV uplift applies to every delivered order (no volume loss from higher prices/basket size).
    """
    extra_cancel = base["total_orders"] * (min(cancel_reduction_pp, base["cancel_rate"] * 100) / 100)
    extra_repeat = base["repeat_orders"] * repeat_uplift_pct / 100
    orders = base["delivered_orders"] + extra_cancel + extra_repeat
    aov = base["aov"] * (1 + aov_uplift_pct / 100)
    revenue = orders * aov
    return {"orders": orders, "aov": aov, "revenue": revenue, "delta": revenue - base["revenue"],
            "delta_pct": (revenue / base["revenue"] - 1) * 100,
            "from_cancel": extra_cancel * base["aov"], "from_repeat": extra_repeat * base["aov"],
            "from_aov": base["delivered_orders"] * base["aov"] * aov_uplift_pct / 100}


def standard_scenarios(base: dict) -> pd.DataFrame:
    sc = {"Baseline": (0, 0, 0), "AOV +5%": (5, 0, 0), "Cancellations -2pp": (0, 2, 0),
          "Repeat purchases +10%": (0, 0, 10), "All three combined": (5, 2, 10)}
    rows = []
    for k, (a, c, r) in sc.items():
        res = run_scenario(base, a, c, r); rows.append({"scenario": k, "revenue": res["revenue"], "uplift": res["delta"], "uplift_pct": res["delta_pct"]})
    return pd.DataFrame(rows)

"""Every documented SQL query must run; star-schema grain and analytics outputs must be sane."""
import pytest

from python.database_loader import load_query_library


def test_query_library_size():
    lib = load_query_library()
    assert len(lib) >= 40 and (lib.level == "advanced").sum() >= 10
    assert lib["name"].is_unique


def test_all_queries_execute(db):
    lib = load_query_library()
    failures = []
    for r in lib.itertuples():
        try:
            res = db.query(r.sql)
            assert len(res.columns) > 0
        except Exception as e:  # pragma: no cover
            failures.append((r.name, str(e)[:120]))
    assert not failures, failures


def test_star_schema_grain_prevents_revenue_inflation(db):
    items = db.query("SELECT SUM(price) s FROM analytics.fact_order_items").iloc[0, 0]
    orders = db.query("SELECT SUM(item_revenue) s FROM analytics.fact_orders").iloc[0, 0]
    assert items == pytest.approx(orders, rel=1e-9)
    n = db.query("SELECT COUNT(*) n, COUNT(DISTINCT order_id) d FROM analytics.fact_orders").iloc[0]
    assert n.n == n.d


def test_rfm_and_segments(db):
    r = db.query("SELECT * FROM analytics.rfm_segments")
    assert r.r_score.between(1, 5).all() and r.m_score.between(1, 5).all() and r.f_score.isin([1, 3, 5]).all()
    assert r.customer_unique_id.is_unique


def test_forecast_beats_or_reports_baselines(db):
    m = db.query("SELECT * FROM analytics.forecast_metrics")
    assert {"Moving average (3m)", "Seasonal naive"} <= set(m.model)
    assert m.RMSE.is_monotonic_increasing


def test_scenario_math():
    from python.scenario import run_scenario
    base = {"delivered_orders": 1000.0, "revenue": 100000.0, "aov": 100.0, "total_orders": 1100.0, "cancel_rate": 0.05, "repeat_orders": 100.0}
    assert run_scenario(base)["revenue"] == pytest.approx(100000)
    assert run_scenario(base, aov_uplift_pct=5)["revenue"] == pytest.approx(105000)
    assert run_scenario(base, repeat_uplift_pct=10)["revenue"] == pytest.approx(101000)

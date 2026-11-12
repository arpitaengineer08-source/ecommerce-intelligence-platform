"""Monthly revenue forecasting with honest baselines.

Models compared on a hold-out of the last H complete months:
  1. Moving average (3m)        - naive level baseline
  2. Seasonal naive             - same month last year
  3. Seasonal naive x YoY drift - same month last year scaled by recent YoY growth
  4. Holt damped trend (ETS)    - statsmodels exponential smoothing
  5. Holt-Winters seasonal      - only when >= 24 months of history exist
Metrics: MAE, RMSE, MAPE (months with ~zero actuals excluded). The best model by RMSE is refit
on all history and projected forward with an approximate 80% interval from hold-out error.
"""
from __future__ import annotations
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from python.database_loader import Database  # noqa: E402

warnings.filterwarnings("ignore")


def monthly_series(db: Database) -> pd.Series:
    df = db.query("""SELECT purchase_month AS month, SUM(item_revenue) AS revenue, MAX(purchase_date) AS last_day
                     FROM analytics.vw_delivered_orders GROUP BY purchase_month ORDER BY purchase_month""")
    df["month"] = pd.to_datetime(df["month"]); df["last_day"] = pd.to_datetime(df["last_day"])
    s = df.set_index("month")["revenue"].astype(float)
    s = s[s >= 0.10 * s.max()]                       # drop sparse start-up months
    last_complete = df["last_day"].iloc[-1] >= (df["month"].iloc[-1] + pd.offsets.MonthEnd(0) - pd.Timedelta(days=2))
    if not last_complete:
        s = s.iloc[:-1]                              # drop partial final month
    s.index = pd.DatetimeIndex(s.index).to_period("M").to_timestamp()
    return s.asfreq("MS")


def _metrics(actual, pred) -> dict:
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    err = a - p
    mask = np.abs(a) > 0.01 * np.mean(np.abs(a))
    return {"MAE": float(np.mean(np.abs(err))), "RMSE": float(np.sqrt(np.mean(err ** 2))),
            "MAPE": float(np.mean(np.abs(err[mask] / a[mask])) * 100) if mask.any() else np.nan}


def _predict(name: str, train: pd.Series, h: int) -> np.ndarray:
    idx = pd.date_range(train.index[-1] + pd.offsets.MonthBegin(1), periods=h, freq="MS")
    if name == "Moving average (3m)":
        return np.repeat(train.iloc[-3:].mean(), h)
    if name in ("Seasonal naive", "Seasonal naive x YoY drift"):
        base = np.array([train.get(d - pd.DateOffset(years=1), np.nan) for d in idx], float)
        if np.isnan(base).any():
            base = np.where(np.isnan(base), train.iloc[-1], base)
        if name.endswith("drift") and len(train) >= 15:
            yoy = train.iloc[-3:].sum() / max(train.iloc[-15:-12].sum(), 1e-9)
            base = base * float(np.clip(yoy, 0.5, 3.0))
        return base
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    if name == "Holt damped trend":
        return ExponentialSmoothing(train, trend="add", damped_trend=True, initialization_method="estimated").fit().forecast(h).values
    if name == "Holt-Winters seasonal":
        return ExponentialSmoothing(train, trend="add", seasonal="mul", seasonal_periods=12,
                                    initialization_method="estimated").fit().forecast(h).values
    raise ValueError(name)


def run_forecast(series: pd.Series, holdout: int = 4, horizon: int = 6):
    models = ["Moving average (3m)", "Seasonal naive", "Seasonal naive x YoY drift", "Holt damped trend"]
    if len(series) - holdout >= 24:
        models.append("Holt-Winters seasonal")
    train, test = series.iloc[:-holdout], series.iloc[-holdout:]
    rows, preds = [], {}
    for m in models:
        try:
            p = _predict(m, train, holdout); preds[m] = p
            rows.append({"model": m, **_metrics(test.values, p)})
        except Exception as e:  # keep the pipeline alive if one model fails
            rows.append({"model": m, "MAE": np.nan, "RMSE": np.nan, "MAPE": np.nan})
    metrics = pd.DataFrame(rows).sort_values("RMSE").reset_index(drop=True)
    best = metrics.iloc[0]["model"]
    # refit best on full history
    fut_idx = pd.date_range(series.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    fut = _predict(best, series, horizon)
    rmse = metrics.iloc[0]["RMSE"]
    width = 1.28 * rmse * np.sqrt(1 + np.arange(horizon) / holdout)
    parts = [pd.DataFrame({"month": series.index, "actual": series.values, "forecast": np.nan, "lower": np.nan, "upper": np.nan, "kind": "actual"}),
             pd.DataFrame({"month": test.index, "actual": test.values, "forecast": preds.get(best, np.full(holdout, np.nan)), "lower": np.nan, "upper": np.nan, "kind": "holdout"}),
             pd.DataFrame({"month": fut_idx, "actual": np.nan, "forecast": fut, "lower": np.maximum(fut - width, 0), "upper": fut + width, "kind": "future"})]
    out = pd.concat(parts, ignore_index=True)
    out["model"] = best
    return metrics, out


LIMITATIONS = ("Only ~20 months of history: annual seasonality is learned from a single cycle, so seasonal models are "
               "fragile. Intervals are approximate (hold-out error). Forecasts assume no new promotions, pricing or "
               "marketing changes. Use for planning ranges, not exact targets.")

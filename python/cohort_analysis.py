"""Cohort retention matrix (customers grouped by first purchase month)."""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from python.database_loader import Database, run_named_query  # noqa: E402


def cohort_table(db: Database) -> pd.DataFrame:
    df = run_named_query(db, "cus_cohort_retention")
    df["cohort_month"] = pd.to_datetime(df["cohort_month"]).dt.strftime("%Y-%m")
    for c in ["month_index", "active_customers", "cohort_size"]:
        df[c] = df[c].astype(int)
    df["retention_pct"] = df["retention_pct"].astype(float)
    return df


def retention_matrix(cohort: pd.DataFrame, max_index: int = 12) -> pd.DataFrame:
    m = cohort[cohort.month_index <= max_index].pivot(index="cohort_month", columns="month_index", values="retention_pct")
    return m


def plot_heatmap(matrix: pd.DataFrame, path=None):
    import matplotlib.pyplot as plt
    import seaborn as sns
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.heatmap(matrix.iloc[:, 1:], annot=True, fmt=".1f", cmap="magma", cbar_kws={"label": "Retention %"}, ax=ax)
    ax.set_title("Monthly cohort retention (% of cohort purchasing again, months after first order)")
    ax.set_xlabel("Months since first purchase"); ax.set_ylabel("Acquisition cohort")
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig

"""Stage 1 - Data ingestion: read the nine Olist CSV files (generating a synthetic stand-in if absent)."""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA_RAW, OLIST_FILES  # noqa: E402

SYNTHETIC_MARKER = DATA_RAW / ".synthetic"


def raw_files_present() -> bool:
    return all((DATA_RAW / f).exists() for f in OLIST_FILES.values())


def data_source() -> str:
    """'synthetic' when the generator produced the files, otherwise 'olist' (real data)."""
    return "synthetic" if SYNTHETIC_MARKER.exists() else "olist"


def ensure_data(use_real: bool = False, n_orders: int = 22000, force_regenerate: bool = False) -> str:
    if use_real:
        if not raw_files_present():
            missing = [f for f in OLIST_FILES.values() if not (DATA_RAW / f).exists()]
            raise FileNotFoundError(f"Missing Olist files in {DATA_RAW}: {missing}\nDownload: "
                                    "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
        SYNTHETIC_MARKER.unlink(missing_ok=True)
        return "olist"
    if force_regenerate or not raw_files_present():
        from python.generate_sample_data import generate
        generate(DATA_RAW, n_orders=n_orders)
    return data_source()


def load_raw() -> dict[str, pd.DataFrame]:
    tables = {}
    for name, fname in OLIST_FILES.items():
        tables[name] = pd.read_csv(DATA_RAW / fname)
    return tables


if __name__ == "__main__":
    src = ensure_data()
    print("data source:", src)
    for k, v in load_raw().items():
        print(f"{k:22s} {v.shape}")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def raw_and_clean():
    from python.data_ingestion import ensure_data, load_raw
    from python.data_cleaning import clean_all
    ensure_data()
    raw = load_raw()
    clean, log = clean_all(raw)
    return raw, clean, log


@pytest.fixture(scope="session")
def db():
    from config import DATABASE_URL, DUCKDB_PATH
    if not DATABASE_URL and not DUCKDB_PATH.exists():
        import run_pipeline
        run_pipeline.run(skip_reports=True)
    from python.database_loader import Database
    d = Database(read_only=True)
    yield d
    d.close()

"""Central configuration for the E-Commerce Intelligence Platform."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
POWERBI_EXPORT = DATA_PROCESSED / "powerbi"
REPORTS = ROOT / "reports"
SQL_DIR = ROOT / "sql"
QUERY_DIR = SQL_DIR / "queries"

# Database: DuckDB file by default (zero setup, PostgreSQL-compatible SQL).
# Set DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/ecommerce to use PostgreSQL.
DUCKDB_PATH = ROOT / "data" / "ecommerce.duckdb"
DATABASE_URL = os.getenv("DATABASE_URL", "")

RANDOM_SEED = 42

OLIST_FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# Brazilian states -> (region, approx. centroid lat, lon)
STATES = {
    "SP": ("Southeast", -22.2, -48.8), "RJ": ("Southeast", -22.3, -42.7),
    "MG": ("Southeast", -18.5, -44.5), "ES": ("Southeast", -19.6, -40.6),
    "RS": ("South", -29.7, -53.5), "PR": ("South", -24.6, -51.6),
    "SC": ("South", -27.3, -50.5), "BA": ("Northeast", -12.9, -41.7),
    "PE": ("Northeast", -8.4, -37.9), "CE": ("Northeast", -5.4, -39.3),
    "MA": ("Northeast", -5.4, -45.4), "PB": ("Northeast", -7.2, -36.8),
    "RN": ("Northeast", -5.8, -36.6), "AL": ("Northeast", -9.6, -36.8),
    "SE": ("Northeast", -10.6, -37.4), "PI": ("Northeast", -7.7, -42.7),
    "GO": ("Central-West", -15.9, -49.8), "DF": ("Central-West", -15.8, -47.8),
    "MT": ("Central-West", -12.6, -55.4), "MS": ("Central-West", -20.5, -54.5),
    "PA": ("North", -3.8, -52.0), "AM": ("North", -4.1, -64.7),
    "TO": ("North", -10.2, -48.3), "RO": ("North", -10.9, -62.8),
    "AC": ("North", -9.0, -70.8), "AP": ("North", 1.4, -51.8),
    "RR": ("North", 2.1, -61.4),
}

# Colour palette shared by the Streamlit app, charts and Power BI theme
PALETTE = {
    "bg": "#0C0E1F", "surface": "#161A35", "edge": "#2A2F5C",
    "iris": "#7C5CFF", "cyan": "#22D3EE", "amber": "#FFB547",
    "mint": "#34E5A1", "rose": "#FF5C8A", "text": "#E9EBFF", "muted": "#9AA0CC",
}

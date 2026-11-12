"""
Database access layer.

* Default engine : DuckDB file  (data/ecommerce.duckdb) -> zero setup, PostgreSQL-compatible SQL dialect.
* PostgreSQL     : set env var DATABASE_URL, e.g.
                   postgresql+psycopg2://postgres:password@localhost:5432/ecommerce

Schemas created:  raw (untouched CSVs) -> staging (cleaned) -> analytics (star schema + model outputs)
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATABASE_URL, DUCKDB_PATH, QUERY_DIR, SQL_DIR  # noqa: E402


class Database:
    def __init__(self, read_only: bool = False, url: str | None = None):
        self.url = DATABASE_URL if url is None else url
        self.is_postgres = bool(self.url)
        if self.is_postgres:
            from sqlalchemy import create_engine
            self.engine = create_engine(self.url)
        else:
            import duckdb
            DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.con = duckdb.connect(str(DUCKDB_PATH), read_only=read_only)

    # ------------------------------------------------------------------ core helpers
    def execute(self, sql: str) -> None:
        if self.is_postgres:
            from sqlalchemy import text
            with self.engine.begin() as conn:
                conn.execute(text(sql))
        else:
            self.con.cursor().execute(sql)

    def query(self, sql: str) -> pd.DataFrame:
        if self.is_postgres:
            return pd.read_sql(sql, self.engine)
        return self.con.cursor().execute(sql).df()

    def run_script(self, path: Path) -> None:
        """Run a .sql file containing several statements."""
        sql = Path(path).read_text(encoding="utf-8")
        sql = re.sub(r"--.*", "", sql)  # strip line comments
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            self.execute(stmt)

    def load_df(self, df: pd.DataFrame, table: str, schema: str) -> None:
        full = f"{schema}.{table}"
        if self.is_postgres:
            df.to_sql(table, self.engine, schema=schema, if_exists="replace", index=False, chunksize=5000, method="multi")
        else:
            self.con.register("_tmp_df", df)
            self.con.execute(f"DROP TABLE IF EXISTS {full}")
            self.con.execute(f"CREATE TABLE {full} AS SELECT * FROM _tmp_df")
            self.con.unregister("_tmp_df")

    def table_exists(self, full_name: str) -> bool:
        try:
            self.query(f"SELECT 1 FROM {full_name} LIMIT 1")
            return True
        except Exception:
            return False

    def close(self) -> None:
        if not self.is_postgres:
            self.con.close()


# ---------------------------------------------------------------------- query library
_BLOCK = re.compile(r"^--\s*name:\s*(\S+)\s*$", re.M)


def load_query_library() -> pd.DataFrame:
    """Parse sql/queries/*.sql. Each block starts with `-- name:` followed by `-- title:`, `-- question:`, `-- level:`."""
    rows = []
    for f in sorted(Path(QUERY_DIR).glob("*.sql")):
        text = f.read_text(encoding="utf-8")
        marks = list(_BLOCK.finditer(text))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = text[m.end():end]
            meta = {"title": "", "question": "", "level": "basic"}
            sql_lines = []
            for line in body.splitlines():
                mm = re.match(r"^--\s*(title|question|level):\s*(.*)$", line)
                if mm:
                    meta[mm.group(1)] = mm.group(2).strip()
                else:
                    sql_lines.append(line)
            rows.append({"name": m.group(1), "module": f.stem, "title": meta["title"], "question": meta["question"],
                         "level": meta["level"], "sql": "\n".join(sql_lines).strip().rstrip(";")})
    return pd.DataFrame(rows)


def run_named_query(db: Database, name: str) -> pd.DataFrame:
    lib = load_query_library()
    hit = lib[lib["name"] == name]
    if hit.empty:
        raise KeyError(f"Unknown query: {name}")
    return db.query(hit.iloc[0]["sql"])

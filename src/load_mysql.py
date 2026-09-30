import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.db import get_engine
from src.ingest import load_all

SQL_DIR = Path("sql")
CLEAN_DIR = Path("data/clean")
REPORTS = Path("reports")
RAW_SCHEMA, CLEAN_SCHEMA = "apple_raw", "apple_clean"
TABLES = ["category", "stores", "products", "sales", "warranty"]  # FK-safe order


def run_sql_file(engine, path: Path) -> None:
    """Execute a .sql file. Assumes no ';' inside string literals (true here)."""
    sql = "\n".join(ln for ln in path.read_text(encoding="utf-8").splitlines()
                    if not ln.strip().startswith("--"))
    with engine.begin() as conn:
        for stmt in sql.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
    print(f"  executed {path.name}")


def truncate_all(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))   # session-scoped, loader-only
        for schema in (RAW_SCHEMA, CLEAN_SCHEMA):
            for t in TABLES:
                conn.execute(text(f"TRUNCATE TABLE {schema}.{t}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    print("  truncated both schemas (rerunnable)")


def load_raw(engine) -> dict[str, pd.DataFrame]:
    tables = load_all()
    for t in TABLES:
        tables[t].to_sql(t, engine, schema=RAW_SCHEMA, if_exists="append",
                         index=False, method="multi", chunksize=1000)
        print(f"  {RAW_SCHEMA}.{t}: {len(tables[t]):,} rows")
    return tables


def load_clean(engine) -> dict[str, pd.DataFrame]:
    out = {}
    for t in TABLES:
        df = pd.read_parquet(CLEAN_DIR / f"{t}.parquet")
        df.to_sql(t, engine, schema=CLEAN_SCHEMA, if_exists="append",
                  index=False, method="multi", chunksize=1000)
        print(f"  {CLEAN_SCHEMA}.{t}: {len(df):,} rows")
        out[t] = df
    return out


def q(engine, sql: str) -> pd.DataFrame:
    return pd.read_sql(text(sql), engine)


def verify(engine, raw_tables, clean_tables) -> None:
    rows = []

    def add(metric, table, pandas_v, mysql_v, tol=0.0):
        ok = abs(pandas_v - mysql_v) <= tol
        rows.append({"metric": metric, "table": table, "pandas": pandas_v,
                     "mysql": mysql_v, "status": "OK" if ok else "FAIL"})

    for t in TABLES:
        n = int(q(engine, f"SELECT COUNT(*) n FROM {RAW_SCHEMA}.{t}")["n"][0])
        add("rows_raw", t, len(raw_tables[t]), n)
    for t in TABLES:
        n = int(q(engine, f"SELECT COUNT(*) n FROM {CLEAN_SCHEMA}.{t}")["n"][0])
        add("rows_clean", t, len(clean_tables[t]), n)

    units = float(q(engine, f"SELECT SUM(quantity) v FROM {CLEAN_SCHEMA}.sales")["v"][0])
    add("units_clean", "sales", float(clean_tables["sales"]["quantity"].sum()), units)

    price_map = dict(zip(clean_tables["products"]["product_id"],
                         clean_tables["products"]["price"]))
    rev_pd = float((clean_tables["sales"]["quantity"]
                    * clean_tables["sales"]["product_id"].map(price_map)).sum())
    rev_mysql = float(q(engine,
        f"SELECT SUM(s.quantity * p.price) v FROM {CLEAN_SCHEMA}.sales s "
        f"JOIN {CLEAN_SCHEMA}.products p ON s.product_id = p.product_id")["v"][0])
    add("revenue_clean", "sales", rev_pd, rev_mysql, tol=0.01)

    df = pd.DataFrame(rows)
    REPORTS.mkdir(exist_ok=True)
    df.to_csv(REPORTS / "load_verification.csv", index=False)
    print(df.to_string(index=False))
    fails = df[df["status"] == "FAIL"]
    print("Load verification:", "ALL OK" if fails.empty else "FAIL — investigate")
    if not fails.empty:
        raise SystemExit(1)


def scorecard(engine) -> None:
    df = q(engine,
        f"""SELECT r.check_id, r.check_name,
                   r.violations AS before_clean, c.violations AS after_clean,
                   c.flagged AS flagged_after,
                   c.violations - c.flagged AS unaccounted
            FROM {RAW_SCHEMA}.vw_audit r
            JOIN {CLEAN_SCHEMA}.vw_audit c USING (check_id)
            ORDER BY unaccounted DESC, before_clean DESC""")
    df = df.astype({"before_clean": int, "after_clean": int,
                    "flagged_after": int, "unaccounted": int})

    def status(r):
        if r.before_clean == 0 and r.after_clean == 0: return "CLEAN"
        if r.after_clean == 0:                         return "FIXED"
        if r.unaccounted == 0:                         return "FLAGGED"
        return "VIOLATION"

    df["status"] = df.apply(status, axis=1)
    df.to_csv(REPORTS / "audit_scorecard.csv", index=False)
    print(df.to_string(index=False))
    bad = df[df["status"] == "VIOLATION"]
    verdict = "ALL ACCOUNTED FOR" if bad.empty else f"{len(bad)} UNACCOUNTED VIOLATIONS"
    print(f"\nScorecard verdict: {verdict}")
    if not bad.empty:
        raise SystemExit(1)


def main() -> None:
    t0 = time.perf_counter()
    engine = get_engine()
    print("1/7 DDL ...");            run_sql_file(engine, SQL_DIR / "01_ddl_raw.sql")
    run_sql_file(engine, SQL_DIR / "02_ddl_clean.sql")
    print("2/7 truncate ...");       truncate_all(engine)
    print("3/7 load apple_raw ..."); raw_tables = load_raw(engine)
    print("4/7 load apple_clean ..."); clean_tables = load_clean(engine)
    print("5/7 audit views ...");    run_sql_file(engine, SQL_DIR / "03_audit_views.sql")
    print("6/7 load verification ..."); verify(engine, raw_tables, clean_tables)
    print("7/7 audit scorecard ...");   scorecard(engine)
    print(f"\nDone in {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
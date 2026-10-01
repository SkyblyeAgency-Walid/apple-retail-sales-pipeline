from pathlib import Path
import pandas as pd
from sqlalchemy import text
from src.db import get_engine
from src.load_mysql import run_sql_file

REPORTS = Path("reports")
TOL = 0.01

SANITY_QUERIES = {
    "flagged_revenue_split": """
        SELECT is_pre_launch_sale, COUNT(*) AS rows_cnt,
               ROUND(SUM(revenue), 2) AS revenue
        FROM apple_clean.vw_sales_revenue
        GROUP BY is_pre_launch_sale""",
    "revenue_by_category": """
        SELECT category_name, ROUND(SUM(revenue), 2) AS revenue,
               SUM(quantity) AS units, COUNT(*) AS rows_cnt
        FROM apple_clean.vw_sales_revenue
        GROUP BY category_name
        ORDER BY revenue DESC""",
    "warranty_by_status": """
        SELECT repair_status, COUNT(*) AS claims,
               ROUND(AVG(days_to_claim), 1) AS avg_days_to_claim
        FROM apple_clean.vw_warranty_performance
        WHERE is_claim_before_sale = 0
        GROUP BY repair_status
        ORDER BY avg_days_to_claim""",
}


def pandas_expected() -> pd.DataFrame:
    """Recompute the flagged split from clean PARQUET — independent of MySQL."""
    sales = pd.read_parquet("data/clean/sales.parquet")
    products = pd.read_parquet("data/clean/products.parquet")
    pm = dict(zip(products["product_id"], products["price"].astype("float64")))
    sales = sales.assign(revenue=sales["quantity"] * sales["product_id"].map(pm))
    return (sales.groupby("is_pre_launch_sale")
                 .agg(rows_cnt=("sale_id", "size"), revenue=("revenue", "sum"))
                 .reset_index())


def main() -> None:
    engine = get_engine()
    print("1/3 building BI layer (dim_date + fact views) ...")
    run_sql_file(engine, Path("sql/04_bi_model.sql"))

    print("2/3 sanity queries ...")
    frames = []
    for name, sql in SANITY_QUERIES.items():
        df = pd.read_sql(text(sql), engine)
        df.insert(0, "query", name)
        frames.append(df)
        print(f"\n=== {name} ===")
        with pd.option_context("display.width", 160):
            print(df.to_string(index=False))
    REPORTS.mkdir(exist_ok=True)
    pd.concat(frames, ignore_index=True).to_csv(REPORTS / "bi_sanity.csv", index=False)

    print("\n3/3 crosscheck: MySQL fact views vs clean parquet ...")
    got = (pd.read_sql(text(SANITY_QUERIES["flagged_revenue_split"]), engine)
             .astype({"revenue": "float64"})
             .sort_values("is_pre_launch_sale").reset_index(drop=True))
    exp = pandas_expected().sort_values("is_pre_launch_sale").reset_index(drop=True)
    assert got["rows_cnt"].tolist() == exp["rows_cnt"].tolist(), "row split mismatch"
    diff = (got["revenue"] - exp["revenue"]).abs().max()
    assert diff < TOL, f"revenue split mismatch: max diff {diff}"
    print(f"  flagged split: rows + revenue match pandas (max diff {diff:.4f})")

    n = pd.read_sql(text("SELECT COUNT(*) AS n FROM apple_clean.dim_date"),
                    engine)["n"][0]
    print(f"  dim_date rows: {n:,}")


if __name__ == "__main__":
    main()
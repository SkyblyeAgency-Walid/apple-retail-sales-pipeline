from pathlib import Path

import pandas as pd

RAW = Path("data/raw")

DTYPES = {
    "category": {"category_id": "string", "category_name": "string"},
    "products": {"Product_ID": "string", "Product_Name": "string",
                 "Category_ID": "string", "Launch_Date": "string", "Price": "string"},
    "sales":    {"sale_id": "string", "sale_date": "string", "store_id": "string",
                 "product_id": "string", "quantity": "string"},
    "stores":   {"Store_ID": "string", "Store_Name": "string",
                 "City": "string", "Country": "string"},
    "warranty": {"claim_id": "string", "claim_date": "string",
                 "sale_id": "string", "repair_status": "string"},
}

FILENAMES = {"category": "category.csv", "products": "products.csv",
             "sales": "sales.csv", "stores": "stores.csv", "warranty": "warranty.csv"}


def load_table(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW / FILENAMES[name], dtype=DTYPES[name])


def load_all() -> dict[str, pd.DataFrame]:
    return {name: load_table(name) for name in FILENAMES}
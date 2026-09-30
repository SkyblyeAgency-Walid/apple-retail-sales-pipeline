from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from pandas.api.types import is_string_dtype

from src.ingest import load_all

REPORTS = Path("reports")

# ---------------------------------------------------------------------------
# Finding ledger — every check flows through record(). Clean checks are counted
# (CHECKS_RUN) but produce no row, so findings.csv IS the defect list.
# ---------------------------------------------------------------------------
@dataclass
class Finding:
    table: str
    check_id: str
    check_name: str
    severity: str
    rows_affected: int
    pct: float
    examples: str
    details: str = ""


FINDINGS: list[Finding] = []
CHECKS_RUN = 0


def record(table: str, check_id: str, check_name: str, severity: str,
           mask, df: pd.DataFrame, n_examples: int = 3) -> None:
    """Run one check. mask = boolean Series/array aligned to df (True = defect)."""
    global CHECKS_RUN
    CHECKS_RUN += 1
    mask = pd.Series(mask, index=df.index).fillna(False).astype(bool)
    n = int(mask.sum())
    if n == 0:
        return
    ex = (df.loc[mask].head(n_examples)
            .apply(lambda r: " | ".join(r.astype(str)), axis=1)
            .str.slice(0, 110)
            .tolist())
    FINDINGS.append(Finding(table, check_id, check_name, severity, n,
                            round(100 * n / len(df), 3), " ;; ".join(ex)))


# ---------------------------------------------------------------------------
# Identity + completeness (generic: run on every table)
# ---------------------------------------------------------------------------
PKS = {"category": "category_id", "products": "Product_ID", "sales": "sale_id",
       "stores": "Store_ID", "warranty": "claim_id"}


def check_identity(tables: dict[str, pd.DataFrame]) -> None:
    for t, df in tables.items():
        pk = PKS[t]
        record(t, "ID-01", f"PK null: {pk}", "CRITICAL", df[pk].isna(), df)
        record(t, "ID-02", f"PK duplicate: {pk}", "CRITICAL",
               df[pk].duplicated(keep=False), df)
        record(t, "ID-03", "full-row duplicate", "MEDIUM",
               df.duplicated(keep=False), df)


def check_completeness(tables: dict[str, pd.DataFrame]) -> None:
    for t, df in tables.items():
        for c in df.columns:
            record(t, "CMP-01", f"nulls in {c}", "MEDIUM", df[c].isna(), df)


# ---------------------------------------------------------------------------
# Conformity: column naming, whitespace, empty strings, date formats
# ---------------------------------------------------------------------------
def check_conformity(tables: dict[str, pd.DataFrame]) -> None:
    for t, df in tables.items():
        bad_cols = [c for c in df.columns if c != c.strip() or c != c.lower()]
        if bad_cols:
            FINDINGS.append(Finding(t, "CNF-01", "non-snake_case column names",
                                    "MEDIUM", len(bad_cols), 0.0, "",
                                    ", ".join(bad_cols)))
        for c in df.columns:
            if is_string_dtype(df[c]):
                record(t, "CNF-02", f"leading/trailing whitespace: {c}", "LOW",
                       df[c].notna() & df[c].str.contains(r"^\s|\s$", na=False), df)
                record(t, "CNF-03", f"empty/whitespace-only (not NULL): {c}", "LOW",
                       df[c].notna() & df[c].fillna("").str.strip().eq(""), df)


DATE_COLS = [("sales", "sale_date"), ("warranty", "claim_date"),
             ("products", "Launch_Date")]
ISO_RE = r"^\d{4}-\d{2}-\d{2}$"
DMY_RE = r"^\d{2}-\d{2}-\d{4}$"


def check_date_formats(tables: dict[str, pd.DataFrame]) -> None:
    """Discover which formats actually occur instead of assuming them."""
    for t, col in DATE_COLS:
        s = tables[t][col]
        iso_n = int(s.str.match(ISO_RE, na=False).sum())
        dmy_n = int(s.str.match(DMY_RE, na=False).sum())
        if iso_n and dmy_n: 
            FINDINGS.append(Finding(
                t, "CNF-04", f"mixed date formats in {col}", "MEDIUM",
                min(iso_n, dmy_n),
                round(100 * min(iso_n, dmy_n) / len(tables[t]), 3),
                "", f"ISO rows={iso_n:,} | DD-MM-YYYY rows={dmy_n:,}"))
        record(t, "CNF-05", f"{col} matches no known date format", "HIGH",
               s.notna() & ~s.str.match(rf"(?:{ISO_RE}|{DMY_RE})", na=False),
               tables[t])


# ---------------------------------------------------------------------------
# Referential integrity — the 4 FK joins from the ERD
# ---------------------------------------------------------------------------
FKS = [("sales", "product_id", "products", "Product_ID"),
       ("sales", "store_id",   "stores",   "Store_ID"),
       ("products", "Category_ID", "category", "category_id"),
       ("warranty", "sale_id", "sales", "sale_id")]


def check_fks(tables: dict[str, pd.DataFrame]) -> None:
    for child_t, child_col, parent_t, parent_col in FKS:
        child, parent = tables[child_t], tables[parent_t]
        mask = child[child_col].notna() & ~child[child_col].isin(parent[parent_col])
        record(child_t, "FK-01",
               f"orphan {child_col} -> {parent_t}.{parent_col}", "CRITICAL",
               mask, child)


# ---------------------------------------------------------------------------
# Numeric domains
# ---------------------------------------------------------------------------
def check_domains(tables: dict[str, pd.DataFrame]) -> None:
    s = tables["sales"]
    qty = pd.to_numeric(s["quantity"], errors="coerce") 
    record("sales", "DOM-01", "quantity not parseable as number", "HIGH",
           qty.isna() & s["quantity"].notna(), s)
    record("sales", "DOM-02", "quantity <= 0", "HIGH", qty <= 0, s)

    p = tables["products"]
    price = p["Price"].fillna("")
    record("products", "DOM-03", "price contains non-numeric characters", "MEDIUM",
           p["Price"].notna() & price.str.contains(r"[^\d.\-]", na=False), p)
    price_num = pd.to_numeric(price.str.replace(r"[^\d.\-]", "", regex=True),
                              errors="coerce")
    record("products", "DOM-04", "price not parseable / <= 0", "HIGH",
           (price_num.isna() & p["Price"].notna()) | (price_num <= 0), p)


# ---------------------------------------------------------------------------
# Temporal logic — cross-table. Each source parsed with its PROVEN format:
# sales is day-first (values like 16-06 can't be months); warranty/products ISO.
# ---------------------------------------------------------------------------
TODAY = pd.Timestamp.today().normalize()


def parse_date_col(s: pd.Series, fmt: str) -> pd.Series:
    return pd.to_datetime(s, format=fmt, errors="coerce")


def check_temporal(tables: dict[str, pd.DataFrame]) -> None:
    prod = tables["products"].copy()
    prod["launch_dt"] = parse_date_col(prod["Launch_Date"], "%Y-%m-%d")
    record("products", "DATE-03", "Launch_Date not parseable as YYYY-MM-DD", "HIGH",
           prod["launch_dt"].isna() & prod["Launch_Date"].notna(), prod)

    sal = tables["sales"].copy()
    sal["sale_dt"] = parse_date_col(sal["sale_date"], "%d-%m-%Y")
    record("sales", "DATE-01", "sale_date not parseable as DD-MM-YYYY", "HIGH",
           sal["sale_dt"].isna() & sal["sale_date"].notna(), sal)
    record("sales", "TIME-03", "sale_date in the future", "HIGH",
           sal["sale_dt"].notna() & (sal["sale_dt"] > TODAY), sal)

    # TIME-01 — sale before product launch
    m = sal.merge(prod[["Product_ID", "launch_dt"]],
                  left_on="product_id", right_on="Product_ID", how="left")
    mask = (m["sale_dt"].notna() & m["launch_dt"].notna()
            & (m["sale_dt"] < m["launch_dt"]))
    record("sales", "TIME-01", "sale before product launch", "HIGH", mask, m)

    war = tables["warranty"].copy()
    war["claim_dt"] = parse_date_col(war["claim_date"], "%Y-%m-%d")
    record("warranty", "DATE-02", "claim_date not parseable as YYYY-MM-DD", "HIGH",
           war["claim_dt"].isna() & war["claim_date"].notna(), war)
    record("warranty", "TIME-04", "claim_date in the future", "HIGH",
           war["claim_dt"].notna() & (war["claim_dt"] > TODAY), war)

    # TIME-02 — claim before sale.
    # NB: if ID-02 fires on sales (dup sale_ids), this left join fans out and
    # counts inflate; the cleaning phase dedups first, and we re-verify after.
    w2 = war.merge(sal[["sale_id", "sale_dt"]], on="sale_id", how="left")
    mask2 = (w2["claim_dt"].notna() & w2["sale_dt"].notna()
             & (w2["claim_dt"] < w2["sale_dt"]))
    record("warranty", "TIME-02", "claim before sale", "HIGH", mask2, w2)


# ---------------------------------------------------------------------------
# Duplicates on natural keys (beyond the PK)
# ---------------------------------------------------------------------------
def check_natural_key_dupes(tables: dict[str, pd.DataFrame]) -> None:
    checks = [("stores", ["Store_Name", "City"], "DUP-01"),
              ("products", ["Product_Name"], "DUP-02"),
              ("category", ["category_name"], "DUP-03")]
    for t, cols, cid in checks:
        df = tables[t]
        record(t, cid, f"duplicate natural key: {' + '.join(cols)}", "MEDIUM",
               df.duplicated(subset=cols, keep=False), df)


# ---------------------------------------------------------------------------
# Value census — the raw material for the rules contract's label mappings
# ---------------------------------------------------------------------------
def build_census(tables: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    census = {}
    for t, col in [("warranty", "repair_status"), ("category", "category_name"),
                   ("stores", "Country"), ("stores", "City"),
                   ("sales", "quantity")]:
        census[f"{t}.{col}"] = tables[t][col].value_counts(dropna=False)
    return census


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------
SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

CSS = ("body{font-family:ui-monospace,Consolas,monospace;font-size:13px;margin:24px}"
       "table{border-collapse:collapse;margin:8px 0 20px}"
       "td,th{border:1px solid #ccc;padding:4px 8px;text-align:left;"
       "vertical-align:top}th{background:#f2f2f2}"
       "h1{font-size:20px}h2{font-size:16px;margin-top:28px}h3{font-size:14px}")


def write_report(census: dict[str, pd.Series]) -> None:
    REPORTS.mkdir(exist_ok=True)
    fdf = pd.DataFrame([asdict(f) for f in FINDINGS])
    if len(fdf):
        fdf["_s"] = fdf["severity"].map(SEV_ORDER)
        fdf = fdf.sort_values(["table", "_s"]).drop(columns="_s").reset_index(drop=True)
    fdf.to_csv(REPORTS / "findings.csv", index=False)

    sev = fdf["severity"].value_counts() if len(fdf) else pd.Series(dtype=int)
    summary = " | ".join(f"{k}: {v}" for k, v in sev.items()) or "no defects found"

    parts = ["<html><head><meta charset='utf-8'>",
             f"<style>{CSS}</style></head><body>",
             "<h1>Damage Report — Raw Profile</h1>",
             f"<p><b>Checks run:</b> {CHECKS_RUN} &nbsp;|&nbsp; "
             f"<b>Checks with findings:</b> {len(fdf)} &nbsp;|&nbsp; "
             f"<b>Severity:</b> {summary}<br>",
             f"Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M} | "
             "scope: raw tables as ingested — nothing cleaned yet</p>"]

    if len(fdf):
        for t, grp in fdf.groupby("table", sort=True):
            parts.append(f"<h2>{t}</h2>")
            parts.append(grp.drop(columns="table").to_html(index=False, border=0))
    else:
        parts.append("<p>No defects detected by the current rule set.</p>")

    parts.append("<h2>Value censuses (low-cardinality columns)</h2>")
    for name, vc in census.items():
        parts.append(f"<h3>{name} — {vc.shape[0]} distinct values</h3>")
        parts.append(vc.rename("rows").to_frame().to_html(border=0))

    parts.append("</body></html>")
    (REPORTS / "damage_report.html").write_text("\n".join(parts), encoding="utf-8")

    print(f"\n=== {CHECKS_RUN} checks run | {len(fdf)} with findings ===")
    print(f"Severity: {summary}")
    if len(fdf):
        with pd.option_context("display.max_rows", 200, "display.width", 160):
            print(fdf[["table", "check_id", "check_name", "severity",
                       "rows_affected", "pct"]].to_string(index=False))
    print(f"\nWrote {REPORTS / 'findings.csv'} and {REPORTS / 'damage_report.html'}")


def main() -> None:
    t0 = time.perf_counter()
    print("Loading raw tables ...")
    tables = load_all()
    for t, df in tables.items():
        print(f"  {t:<10} {len(df):>10,} rows")

    check_identity(tables)
    check_completeness(tables)
    check_conformity(tables)
    check_date_formats(tables)
    check_fks(tables)
    check_domains(tables)
    check_temporal(tables)
    check_natural_key_dupes(tables)

    write_report(build_census(tables))
    print(f"Done in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
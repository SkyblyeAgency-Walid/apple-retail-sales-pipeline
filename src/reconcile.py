from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from src.ingest import load_all

CLEAN_DIR = Path("data/clean")
QUAR_DIR = Path("data/quarantine")
REPORTS_DIR = Path("reports")

TOL = 0.01

LEDGER: list[dict] = []


def add(metric: str, table: str, raw, clean, quar, note: str = "") -> None:
    raw, clean, quar = float(raw), float(clean), float(quar)
    var = raw - (clean + quar)
    LEDGER.append({
        "metric": metric, "table": table,
        "raw": raw, "clean": clean, "quarantined": quar,
        "variance": var,
        "status": "OK" if abs(var) < TOL else "FAIL",
        "note": note,
    })


def quarantine_frames(table: str) -> list[pd.DataFrame]:
    """Every quarantine partition written for this table (generic: 0..n files)."""
    if not QUAR_DIR.exists():
        return []
    return [pd.read_csv(f) for f in sorted(QUAR_DIR.glob(f"{table}_*.csv"))]


def main() -> None:
    t0 = time.perf_counter()
    raw = load_all()
    clean = {t: pd.read_parquet(CLEAN_DIR / f"{t}.parquet") for t in raw}

    # --- 1) ROWS: raw = clean + quarantined --------------------------------
    for t in raw:
        quar = sum(len(q) for q in quarantine_frames(t))
        add("rows", t, len(raw[t]), len(clean[t]), quar)

    # --- 2) UNITS: sales.quantity ------------------------------------------
    raw_units = pd.to_numeric(raw["sales"]["quantity"])
    cln_units = clean["sales"]["quantity"]
    quar_units = sum(float(pd.to_numeric(q["quantity"]).sum())
                     for q in quarantine_frames("sales"))
    add("units", "sales", raw_units.sum(), cln_units.sum(), quar_units)

    # --- 3) REVENUE: quantity x price, joined to products ------------------
    # Price lookup from each side's own product table (raw names vs clean names).
    # Independence check: a missing price lookup would silently NaN-out revenue,
    # so we assert lookup completeness first (FK integrity -> revenue integrity).
    raw_price_map = dict(zip(raw["products"]["Product_ID"],
                             pd.to_numeric(raw["products"]["Price"])))
    cln_price_map = dict(zip(clean["products"]["product_id"],
                             clean["products"]["price"]))

    raw_hits = raw["sales"]["product_id"].map(raw_price_map)
    cln_hits = clean["sales"]["product_id"].map(cln_price_map)
    assert raw_hits.notna().all(), "raw sale references a product with no price"
    assert cln_hits.notna().all(), "clean sale references a product with no price"

    raw_rev = (raw_units * raw_hits).sum()
    cln_rev = (cln_units * cln_hits).sum()

    quar_rev = 0.0
    for q in quarantine_frames("sales"):
        q_hits = q["product_id"].map(cln_price_map)
        assert q_hits.notna().all(), "quarantined sale has no price lookup"
        quar_rev += float((pd.to_numeric(q["quantity"]) * q_hits).sum())

    add("revenue", "sales", raw_rev, cln_rev, quar_rev,
        "quantity x price, joined to products")

    # --- informational (exec-summary material, NOT part of the identity) ---
    sales = clean["sales"]
    rev_series = cln_units * cln_hits
    pre = sales["is_pre_launch_sale"] == 1
    info = pd.DataFrame([
        {"segment": "clean rows", "rows": int((~pre).sum()),
         "units": float(cln_units[~pre].sum()), "revenue": float(rev_series[~pre].sum())},
        {"segment": "FLAGGED pre-launch rows", "rows": int(pre.sum()),
         "units": float(cln_units[pre].sum()), "revenue": float(rev_series[pre].sum())},
    ])
    gross = float(rev_series.sum())
    info["rev_share_%"] = (info["revenue"] / gross * 100).round(2)

    # --- verdict ------------------------------------------------------------
    REPORTS_DIR.mkdir(exist_ok=True)
    df = pd.DataFrame(LEDGER)
    df.to_csv(REPORTS_DIR / "reconciliation.csv", index=False)

    print("=== Reconciliation ledger:  raw = clean + quarantined (+variance) ===")
    with pd.option_context("display.width", 160):
        print(df.to_string(index=False))
    fails = df[df["status"] == "FAIL"]
    print("\nVerdict:", "ALL TIES OK" if fails.empty
          else f"FAIL — {len(fails)} unexplained variance(s): investigate before shipping")
    print("\n=== Informational: flagged-segment exposure (clean table) ===")
    with pd.option_context("display.width", 160):
        print(info.to_string(index=False))
    print(f"\nGross revenue: {gross:,.2f}")

    if not fails.empty:
        raise SystemExit(1)
    print(f"\nDone in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
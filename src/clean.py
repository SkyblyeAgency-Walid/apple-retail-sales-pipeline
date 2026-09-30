from __future__ import annotations

import json
import operator
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml
from pandas.api.types import is_string_dtype

from src.ingest import load_all

CONTRACT_PATH = Path("docs/rules_contract.yaml")
CLEAN_DIR = Path("data/clean")
QUAR_DIR = Path("data/quarantine")
REPORTS_DIR = Path("reports")

LOG: list[dict] = []
QUAR: dict[tuple[str, str], pd.DataFrame] = {}

DOMAIN_OPS = {">=": operator.ge, ">": operator.gt,
              "<=": operator.le, "<": operator.lt, "==": operator.eq}

DTYPE_ALIASES = {"datetime64": "datetime64[ns]"}


def resolve_dtype(name: str) -> str:
    """Translate contract dtype aliases into pandas-native dtype strings."""
    return DTYPE_ALIASES.get(name, name)


def log(run_id: str, stage: str, rule: dict, table: str,
        rows_affected: int, rows_total: int, details: str) -> None:
    LOG.append({
        "run_id": run_id,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": stage,
        "rule_id": rule["rule_id"],
        "check_id": rule.get("check_id", ""),
        "action": rule.get("action", "FIX"),
        "table": table,
        "rows_affected": int(rows_affected),
        "rows_total": int(rows_total),
        "details": details,
    })


# ---------------------------------------------------------------------------
# Conform operations (multi-table)
# ---------------------------------------------------------------------------
def op_rename(tables: dict, rule: dict, run_id: str) -> dict:
    for table, mapping in rule["mapping"].items():
        tables[table] = tables[table].rename(columns=mapping)
        log(run_id, "conform", rule, table, 0, len(tables[table]),
            f"renamed columns: {mapping}")
    return tables


def op_strip(tables: dict, rule: dict, run_id: str) -> dict:
    for table in rule["tables"]:
        df = tables[table]
        changed = pd.Series(False, index=df.index)
        for c in df.columns:
            if is_string_dtype(df[c]):
                stripped = df[c].str.strip()
                changed |= (df[c] != stripped).fillna(False)
                df[c] = stripped
        tables[table] = df
        log(run_id, "conform", rule, table, int(changed.sum()), len(df),
            "trimmed leading/trailing whitespace")
    return tables


CONFORM_OPS = {"rename_columns": op_rename, "strip_whitespace": op_strip}


# ---------------------------------------------------------------------------
# Type rules — single table, failures QUARANTINE per contract
# ---------------------------------------------------------------------------
def apply_type_rule(tables: dict, rule: dict, run_id: str) -> dict:
    table, col = rule["table"], rule["column"]
    df = tables[table]
    n0 = len(df)

    if rule["to"] == "datetime64":
        converted = pd.to_datetime(df[col], format=rule["format"], errors="coerce")
        bad = converted.isna()
        reason = f"{col} null or not parseable as {rule['format']}"
    else:
        converted = pd.to_numeric(df[col], errors="coerce")
        bad = converted.isna()
        reason = f"{col} null or not parseable as {rule['to']}"
        if "domain" in rule:
            op_name, bound = rule["domain"].split()
            domain_ok = DOMAIN_OPS[op_name](converted, float(bound))
            bad = bad | (converted.notna() & ~domain_ok)
            reason += f" or domain {rule['domain']} violated"
        if rule.get("integral"):
            bad = bad | (converted.notna() & (converted != converted.round()))
            reason += " or non-integer value"

    n_bad = int(bad.sum())
    if n_bad:  # expected 0 per profiler; if a file appears here, the contract worked
        out = df.loc[bad].copy()
        out["quarantine_rule"] = rule["rule_id"]
        out["quarantine_reason"] = reason
        QUAR[(table, rule["rule_id"])] = out
        df = df.loc[~bad].copy()
        converted = converted.loc[~bad]

    df[col] = converted.astype(resolve_dtype(rule["to"]))
    tables[table] = df
    log(run_id, "type", rule, table, n_bad, n0, reason)
    return tables


# ---------------------------------------------------------------------------
# Defect rules — flag logic registry. Each returns a boolean mask on df.
# Order guarantee: conform ran first (snake_case names), types ran second
# (dates are datetime64), so these comparisons are safe.
# ---------------------------------------------------------------------------
def flag_sale_before_launch(df, rule, tables):
    launch = tables["products"].set_index("product_id")["launch_date"]
    row_launch = df["product_id"].map(launch)
    return (df["sale_date"].notna() & row_launch.notna()
            & (df["sale_date"] < row_launch))


def flag_claim_before_sale(df, rule, tables):
    sale_dt = tables["sales"].set_index("sale_id")["sale_date"]
    row_sale = df["sale_id"].map(sale_dt)
    return (df["claim_date"].notna() & row_sale.notna()
            & (df["claim_date"] < row_sale))


def flag_duplicate_natural_key(df, rule, tables):
    return df.duplicated(subset=rule["columns"], keep=False)


FLAG_LOGIC = {"sale_before_launch": flag_sale_before_launch,
              "claim_before_sale": flag_claim_before_sale,
              "duplicate_natural_key": flag_duplicate_natural_key}


def apply_flag_rule(tables: dict, rule: dict, run_id: str) -> dict:
    table = rule["table"]
    df = tables[table]
    mask = FLAG_LOGIC[rule["logic"]](df, rule, tables)
    df[rule["flag_column"]] = mask.astype("int8")
    tables[table] = df
    log(run_id, "defect", rule, table, int(mask.sum()), len(df),
        f"flagged by {rule['logic']}")
    return tables


# ---------------------------------------------------------------------------
# Crosscheck: engine counts MUST equal profiler counts per check_id.
# This is the profiler->engine reconciliation. Mismatch = stop and investigate.
# ---------------------------------------------------------------------------
def crosscheck() -> None:
    fpath = REPORTS_DIR / "findings.csv"
    if not fpath.exists():
        print("  (findings.csv not found — crosscheck skipped)")
        return
    prof = pd.read_csv(fpath).set_index("check_id")["rows_affected"].to_dict()
    mismatches = []
    for e in LOG:
        cid = e["check_id"]
        if cid and cid in prof:
            ok = prof[cid] == e["rows_affected"]
            print(f"  crosscheck {cid}: profiler={prof[cid]:,} "
                  f"engine={e['rows_affected']:,} -> {'OK' if ok else 'MISMATCH'}")
            if not ok:
                mismatches.append(cid)
    if mismatches:
        raise SystemExit(f"STOP: engine/profiler count mismatch for {mismatches} — "
                         "do not ship cleaned outputs until explained.")


# ---------------------------------------------------------------------------
# Outputs + per-table row accounting (the seed of the Phase 5 ledger)
# ---------------------------------------------------------------------------
def write_outputs(tables: dict, raw_counts: dict, contract_version: str,
                  run_id: str) -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    QUAR_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)

    for t, df in tables.items():
        df.to_parquet(CLEAN_DIR / f"{t}.parquet", index=False)

    for (table, rule_id), qdf in QUAR.items():
        qdf.to_csv(QUAR_DIR / f"{table}_{rule_id}.csv", index=False)

    pd.DataFrame(LOG).to_csv(REPORTS_DIR / "cleaning_log.csv", index=False)

    summary = {"run_id": run_id, "contract_version": contract_version, "tables": {}}
    rows = []
    for t, df in tables.items():
        quar = sum(len(q) for (tb, _), q in QUAR.items() if tb == t)
        flags = {e["rule_id"]: e["rows_affected"] for e in LOG
                 if e["stage"] == "defect" and e["table"] == t}
        assert len(df) + quar == raw_counts[t], f"row accounting broke for {t}"
        summary["tables"][t] = {"raw_rows": raw_counts[t], "clean_rows": len(df),
                                "quarantined_rows": quar, "flag_rows": flags}
        rows.append({"table": t, "raw": raw_counts[t], "clean": len(df),
                     "quarantined": quar,
                     "flagged": sum(flags.values())})
    (REPORTS_DIR / "clean_summary.json").write_text(json.dumps(summary, indent=2))

    print("\n=== Row accounting (clean + quarantined == raw, asserted) ===")
    print(pd.DataFrame(rows).to_string(index=False))


def main() -> None:
    t0 = time.perf_counter()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    contract = yaml.safe_load(CONTRACT_PATH.read_text())
    print(f"Rules contract v{contract['contract_version']} — run {run_id}\n")

    tables = load_all()
    raw_counts = {t: len(df) for t, df in tables.items()}
    print("Raw rows:", {t: f"{n:,}" for t, n in raw_counts.items()})

    for rule in contract.get("conform_rules", []):
        tables = CONFORM_OPS[rule["operation"]](tables, rule, run_id)
    for rule in contract.get("type_rules", []):
        tables = apply_type_rule(tables, rule, run_id)
    for rule in contract.get("defect_rules", []):
        tables = apply_flag_rule(tables, rule, run_id)

    print("\nCrosschecking engine counts vs profiler findings ...")
    crosscheck()

    write_outputs(tables, raw_counts, contract["contract_version"], run_id)

    print(f"\n=== cleaning_log: {len(LOG)} rule executions ===")
    with pd.option_context("display.width", 160):
        print(pd.DataFrame(LOG)[["stage", "rule_id", "check_id", "table",
                                 "action", "rows_affected",
                                 "rows_total"]].to_string(index=False))
    print(f"\nDone in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
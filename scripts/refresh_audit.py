from pathlib import Path
import pandas as pd
from src.db import get_engine
from src.load_mysql import run_sql_file, scorecard


def crosscheck_vs_profiler() -> None:
    sc = pd.read_csv("reports/audit_scorecard.csv")
    prof = pd.read_csv("reports/findings.csv").set_index("check_id")["rows_affected"].to_dict()

    mismatches = []
    for _, r in sc.iterrows():
        cid = r["check_id"]
        if cid not in prof:
            continue
        p = int(prof[cid])
        if int(r["before_clean"]) != p:
            mismatches.append(f"{cid}: MySQL raw={r['before_clean']} vs pandas={p}")
        if int(r["after_clean"]) != p:
            mismatches.append(f"{cid}: MySQL clean={r['after_clean']} vs pandas={p} "
                              "(quarantine empty -> retention expected)")

    if mismatches:
        raise SystemExit("STOP — audit disagrees with independent profiler count:\n  "
                         + "\n  ".join(mismatches))
    n = sc["check_id"].isin(prof).sum()
    print(f"External crosscheck: MySQL raw+clean agree with pandas profiler "
          f"on all {n} overlapping defect checks.")


def main() -> None:
    engine = get_engine()
    run_sql_file(engine, Path("sql/03_audit_views.sql"))
    scorecard(engine)
    crosscheck_vs_profiler()


if __name__ == "__main__":
    main()
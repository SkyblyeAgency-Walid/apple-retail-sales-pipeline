# Power Query Rerunnable Recipe — Apple Retail Sales Pipeline

**Version** 1.0.0 · **Date** 2026-09-30
**Contract** `docs/rules_contract.yaml` v1.0.0 (Python engine = source of truth)
**Workbook** `powerquery/Apple_Retail_PowerQuery_Recipe.xlsx`
**Scripts** `powerquery/m/*.pq` — one file per query, pasted into the Advanced Editor

---

## 1. Purpose

This workbook re-implements the project's data-quality contract in Power Query (M),
so the pipeline can be re-run on fresh raw CSVs by a business user — no Python needed.

It is a **portability proof**, not the source of truth: the Python engine
(`src/clean.py`) remains canonical (Decision D21). Where the two disagree,
the engine wins and this workbook is corrected.

**Design decision D20:** `sales` (1,040,200 rows) loads to the **Data Model**, not a
worksheet — Excel's ceiling is 1,048,576 rows (8,376 rows of headroom). Small tables
and the audit/reconciliation deliverables load to worksheets where reviewers see them.

## 2. Verified results — four independent engines agree

| Metric                          | pandas (profiler/engine) | MySQL audit | Excel / Power Query |
|---------------------------------|-------------------------:|------------:|--------------------:|
| Sales rows                      |                1,040,200 |   1,040,200 |           1,040,200 |
| Units                           |                5,721,344 |   5,721,344 |           5,721,344 |
| Gross revenue                   |         6,166,293,030.00 | 6,166,293,030 |       6,166,293,030 |
| Revenue, unflagged rows         |         3,331,386,620.00 | 3,331,386,620 |       3,331,386,620 |
| Revenue, flagged pre-launch     |         2,834,906,410.00 (45.97%) | 2,834,906,410 | 2,834,906,410 |
| FK orphans (4 checks)           |                        0 |           0 |                   0 |

In-workbook reconciliation variance: **rows 0 · units 0 · revenue 0.00**.
Non-zero variance on any refresh = gate failure, stop and investigate (§9).

## 3. Prerequisites

- Desktop Excel 2016+ (Power Query built in)
- The five raw CSVs in one folder (`data/raw`)
- Full refresh takes 5-15 min (1M-row Data Model); background refresh disabled (§7)

## 4. Contract traceability — rule to M implementation

| Rule | Evidence | M implementation |
|---|---|---|
| R-CNF-001 snake_case renames | CNF-01 | `Table.RenameColumns` in `clean_products`, `clean_stores` |
| R-CNF-002 trim whitespace | CNF-02 | `Text.Trim` transform in every `clean_*` |
| R-TYPE-001 sale_date DD-MM-YYYY | DATE-01 | `fnCleanSaleDate` in `clean_sales` (day-first proven: day > 12 values) |
| R-TYPE-002 claim_date ISO | DATE-02 | `fnCleanISODate` in `clean_warranty` |
| R-TYPE-003 launch_date ISO | — | `fnCleanISODate` in `clean_products` |
| R-TYPE-004 quantity int >= 1 | DOM-01/02 | `Number.FromText` + `>= 1` filter in `clean_sales` |
| R-TYPE-005 price > 0 | DOM-03/04 | `Number.FromText` + `> 0` filter in `clean_products` |
| R-TIME-001 pre-launch flag | TIME-01 | `flagged_sales[is_pre_launch_sale]` |
| R-TIME-002 claim-before-sale | TIME-02 | `flagged_warranty[is_claim_before_sale]` |
| R-DUP-001 duplicate stores | DUP-01 | `flagged_stores` — self group-by + left-outer merge |
| R-DUP-002 ambiguous product name | DUP-02 | `flagged_products` — same pattern |
| FK integrity x4 | FK-01..04 | `audit_fk` — LeftAnti row counts |
| Reconciliation | — | `reconciliation` — raw side computed from **staging** (independence rule) |

## 5. Build order

Every query: `Home -> New Source -> Blank Query` -> rename to the EXACT manifest name ->
`Home -> Advanced Editor` -> paste the matching `m/*.pq` script -> `Done`.
Only the parameter is UI-built. Order matters (dependencies resolve top-down).

| # | Query | Kind | Load destination |
|---|---|---|---|
| 0 | `pSourceFolder` | Parameter (UI) | — |
| 1 | `fnCleanSaleDate` | Function | — |
| 2 | `fnCleanISODate` | Function | — |
| 3 | `stg_category` | Staging | Connection only |
| 4 | `stg_products` | Staging | Connection only |
| 5 | `stg_sales` | Staging | Connection only |
| 6 | `stg_stores` | Staging | Connection only |
| 7 | `stg_warranty` | Staging | Connection only |
| 8 | `clean_category` | Clean | Table -> `Category` |
| 9 | `clean_products` | Clean | Connection only |
| 10 | `clean_sales` | Clean | Connection only |
| 11 | `clean_stores` | Clean | Connection only |
| 12 | `clean_warranty` | Clean | Connection only |
| 13 | `flagged_stores` | Flag | Table -> `Stores` |
| 14 | `flagged_products` | Flag | Table -> `Products` |
| 15 | `flagged_warranty` | Flag | Table -> `Warranty` |
| 16 | `flagged_sales` | Flag | **Data Model** |
| 17 | `audit_fk` | Audit | Table -> `Audit_FK` |
| 18 | `reconciliation` | Audit | Table -> `Reconciliation` |

### Steps

1. **Workbook skeleton** — tabs: `Rules`, `Audit_FK`, `Reconciliation`, `Stores`, `Products`, `Category`, `Warranty`.
2. **Parameter** — `Manage Parameters -> New`: name `pSourceFolder`, type Text, value = full path to the raw folder. All staging queries read it; one edit re-points the recipe.
3. **Functions** — paste `fnCleanSaleDate.pq`, `fnCleanISODate.pq`.
4. **Staging** — five queries, as-landed: all text, original mixed-case headers, Connection only.
5. **Clean** — five queries (conform + type rules). Parse failures are filtered out — expected count 0; the `reconciliation.rows` variance is the detector (§10).
6. **Flags** — four queries adding contract flags; `flagged_sales` also carries `price` and `revenue = quantity x price` for the Data Model.
7. **Audit + reconciliation** — `audit_fk` (4 x LeftAnti counts); `reconciliation` (raw from staging, clean from clean/flagged; `variance = raw - clean`).
8. **Load destinations** — per the table; for `flagged_sales` tick **Add to the Data Model**. Then one `Close & Load`.
9. **Data Model demo** — PivotTable from the Data Model; measure `Total Revenue := SUM(flagged_sales[revenue])`; slicers on `is_pre_launch_sale`, `category_name`.

Formatting tips: `Reconciliation` — rows/units as whole numbers, revenue/variance 2-dp;
`Rules` tab — contract summary (rule_id, action, evidence) plus the sentence:
*"Source of truth: Python engine, contract v1.0.0. This workbook re-implements the
same rules in Power Query for portability."*

## 6. Verification targets

| Query | Expected |
|---|---|
| `stg_sales` = `clean_sales` = `flagged_sales` | 1,040,200 rows each (equal = quarantine path empty) |
| `flagged_warranty` | 30,000 rows · 2,687 flagged |
| `flagged_products` | 89 rows · 2 flagged |
| `flagged_stores` | 75 rows · 12 flagged |
| `audit_fk` | violations 0 / 0 / 0 / 0 |
| `reconciliation` | variance 0 / 0 / 0.00 |
| Slicer all / 0 / 1 | 6,166,293,030 / 3,331,386,620 / 2,834,906,410 |

## 7. Performance notes

- Disable **background refresh** on all queries (Queries & Connections -> Properties). Refresh on demand.
- Dimensions are buffered before merges (`Table.Buffer(clean_products)`) — tiny tables, free speedup.
- CSV sources do not fold; everything runs in memory. Staging is connection-only so nothing is materialized twice.
- Never schedule this workbook for unattended auto-refresh.

## 8. Screenshot checklist (portfolio)

1. Parameter dialog showing `pSourceFolder`
2. `clean_products` Applied Steps — the snake_case rename visible
3. `Reconciliation` tab — variance 0 / 0 / 0.00
4. `Audit_FK` tab — four zeros
5. PivotTable, slicer at `is_pre_launch_sale = 1`, showing 2,834,906,410 (45.97%)
6. Queries & Connections pane showing load destinations

## 9. Rerunning on fresh data

1. Put the five CSVs (same file names) in a folder.
2. Edit `pSourceFolder` — the only edit.
3. `Refresh All`.
4. **Gate:** `Reconciliation` variance 0 / 0 / 0.00 and `Audit_FK` all zeros.
   Non-zero = STOP and investigate. The tab is the alarm — never edit numbers to pass it.

## 10. Deliberate scope limits

- The PQ port *filters* parse failures (expected 0) instead of writing quarantine files;
  the Python engine writes `data/quarantine/` canonically. The `reconciliation.rows`
  variance is the in-workbook detector of any loss.
- No MySQL load, no dim_date, no ERD here — those live in the Python/SQL pipeline.
- If the Data Model pushes the workbook past ~100 MB, distribute the connection-only copy.

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Undefined variable` on paste | Query name does not match name in code | Rename to exact manifest name |
| "Column already exists" on rename | Original not removed first | Follow `clean_sales` pattern: add -> filter -> remove -> rename |
| Formula.Firewall / privacy error | Multi-source query combine | File -> Options -> Privacy -> ignore levels (this workbook) |
| Data Model load hangs | Background refresh competing | Disable it; refresh foreground, dims first |
| Reconciliation variance not 0 | Real row/type loss — gate failure | STOP; compare staging vs clean counts; never edit the tab |

# Decisions & Rationale - Apple Retail Sales Pipeline

======================================================================
category.csv  |  rows: 10  |  memory: 0.0 MB
columns: ['category_id', 'category_name']
category_id      str
category_name    str
  category_id category_name
0       CAT-1        Laptop
1       CAT-2         Audio
2       CAT-3        Tablet
======================================================================
products.csv  |  rows: 89  |  memory: 0.0 MB
columns: ['Product_ID', 'Product_Name', 'Category_ID', 'Launch_Date', 'Price']
Product_ID        str
Product_Name      str
Category_ID       str
Launch_Date       str
Price           int64
  Product_ID      Product_Name Category_ID Launch_Date  Price
0        P-1           MacBook       CAT-1  2023-09-17   1149
1        P-2  MacBook Air (M1)       CAT-1  2023-11-11   1783
2        P-3  MacBook Air (M2)       CAT-1  2020-05-24   1588
======================================================================
sales.csv  |  rows: 1,040,200  |  memory: 69.5 MB
columns: ['sale_id', 'sale_date', 'store_id', 'product_id', 'quantity']
sale_id         str
sale_date       str
store_id        str
product_id      str
quantity      int64
     sale_id   sale_date store_id product_id  quantity
0    YG-8782  16-06-2023    ST-10       P-38        10
1  QX-999001  13-04-2022    ST-63       P-48        10
2   JG-46890  05-07-2021    ST-26       P-79         5
======================================================================
stores.csv  |  rows: 75  |  memory: 0.0 MB
columns: ['Store_ID', 'Store_Name', 'City', 'Country']
Store_ID      str
Store_Name    str
City          str
Country       str
  Store_ID             Store_Name           City        Country
0     ST-1     Apple Fifth Avenue       New York  United States
1     ST-2     Apple Union Square  San Francisco  United States
2     ST-3  Apple Michigan Avenue        Chicago  United States
======================================================================
warranty.csv  |  rows: 30,000  |  memory: 2.0 MB
columns: ['claim_id', 'claim_date', 'sale_id', 'repair_status']
claim_id         str
claim_date       str
sale_id          str
repair_status    str
   claim_id  claim_date    sale_id repair_status
0  CL-58750  2024-01-30    YG-8782     Completed
1   CL-8874  2024-06-25  QX-999001       Pending
2  CL-14486  2024-08-13   JG-46890       Pending
======================================================================


Decision log (append-only). One decision per entry. Entries are never edited
after commit; corrections get a new entry that references the old one.

- D1. Column naming target standard: lowercase snake_case. Source mixes
  Product_ID vs sale_id; conform at ingest into the clean schema, originals
  preserved in the raw schema.
- D2. Raw data is immutable; all repairs happen downstream, originals
  preserved (raw CSVs checksummed, MySQL raw schema as-landed).
- D3. Disposition policy: FIX / FLAG / QUARANTINE - never silent DELETE.
  Every row is accounted for: clean + quarantined + variance = raw.
- D4. PK gap check dropped: IDs are prefixed strings (P-1, YG-8782, ST-1),
  not sequential integers; duplicates are covered by check ID-02.
- D5. Pre-launch sales (TIME-01, 493,143 rows = 47.4%) -> FLAG, never
  quarantine. Both dates are individually valid; the conflict is systemic.
  Quarantining would destroy half the fact table; the flag lets BI
  include/exclude deliberately with one filter.
- D6. Claims before sale (TIME-02, 2,687 rows) -> FLAG. Source truth is
  unknowable from the data alone; the signal is preserved.
- D7. Duplicate stores (DUP-01, 6 pairs = 12 of 75 rows) -> FLAG, not merge.
  No authoritative source confirms identity; merging would fabricate
  certainty and silently remap sales FKs to an assumed survivor.
- D8. HomePod mini pair (DUP-02) -> FLAG as ambiguous, retain both SKUs.
  Conflicting category/price imply distinct products; report by product_id,
  never by name.
- D9. R-DOM-005 (repair_status label mapping) dropped: the value census
  showed exactly 4 canonical labels. Profiling prevented a fix for a
  nonexistent defect.
- D10. An empty quarantine folder is the CORRECT outcome, not an omission:
  the profiler already proved parse/domain cleanliness; the quarantine path
  exists so tomorrow's dirty data fails safely instead of corrupting outputs.
- D11. Contract dtypes are human aliases; the engine resolves them via
  DTYPE_ALIASES (datetime64 -> datetime64[ns]). The signed-off contract is
  never bent to implementation quirks; engine bugs are fixed in the engine.
- D12. Unpinned pandas drifted to 3.x (unit-less datetime64 astype is now a
  hard error). requirements.lock exists; all runs must use it.
- D13. The raw schema is constraint-free by design: constraints are
  assertions of the clean contract and belong in apple_clean only.
- D14. FOREIGN_KEY_CHECKS=0 is used only for truncate (rerunnability),
  never for load.
- D15. to_sql(method=multi, chunksize=1000) is fine at local scale;
  LOAD DATA INFILE is the production-scale alternative.
- D16. Audit metrics must be unit-consistent across before/after (rows,
  never groups). The v1 scorecard compared rows (raw) vs groups (clean) for
  the DUP checks; caught on first run, views corrected, scorecard
  regenerated without a data reload.
- D17. unaccounted=0 proves internal consistency, not correctness: the v1
  clean-side counts were wrong in a way that matched the flagged count, so
  the two wrong numbers agreed. Fix: unit-consistent row counts plus an
  automated three-way crosscheck (pandas profiler <-> MySQL raw <->
  MySQL clean). Corollary: rerunning a runner is not deploying a fix - the
  artifact it executes must contain the change.
- D18. dim_date is materialized, not a view: the calendar span exceeds
  MySQL's default cte_max_recursion_depth (1000), so a recursive-CTE view
  would fail at query time.
- D19. Fact views expose the contract flags: exclusion of flagged rows is
  the analyst's one-filter decision at query time, never a pre-deletion in
  the pipeline.
- D20. Power Query workbook: sales loads to the Data Model (worksheet
  ceiling 1,048,576 vs 1,040,200 rows = 8,376 rows of headroom); dims,
  audit and reconciliation load to worksheets.
- D21. The Power Query recipe is a portability demonstration; the Python
  engine remains the source of truth. Where the two disagree, the engine
  wins and the workbook is corrected.

- D22. A real password was found committed as a default parameter in src/db.py
  (and in compiled __pycache__ bytecode). Caught by the pre-push secrets gate,
  BEFORE any public push. Remediation: fail-fast credential handling (no
  defaults), __pycache__ and the 183MB workbook removed from tracking, history
  rewritten with git filter-repo (secret string replaced, large artifacts
  purged), password rotated. Rule: credentials live in environment variables
  only - never in code, never in history.

- D23. Least-privilege database access: the pipeline authenticates as a
  dedicated apple_etl account scoped to apple_raw.* and apple_clean.* only
  (SELECT, INSERT, CREATE, DROP, INDEX, ALTER, CREATE VIEW, REFERENCES).
  No UPDATE/DELETE grants - the account physically cannot mutate stored rows,
  mirroring the append-only load design. Root remains admin-only with its own
  rotated password. Schemas pre-created by root so the pipeline holds no
  global CREATE. Verified by negative tests (CREATE DATABASE / DELETE denied).

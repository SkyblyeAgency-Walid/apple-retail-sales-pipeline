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


D1. Column naming target standard: lowercase snake_case (source is mixed-case: Product_ID vs sale_id).
D2 Raw data is immutable; all repairs happen downstream, originals preserved.
D3 Disposition policy: FIX / FLAG / QUARANTINE. Never silent DELETE.
D5. Pre-launch sales → FLAG, never quarantine (47.4% of fact table; both dates individually valid).
D6. Claims before sale → FLAG (source truth unknowable; signal preserved).
D7. Duplicate stores (6 pairs) → FLAG, not merge: no authoritative source confirms identity; merging would       fabricate certainty and silently remap sales FKs.
D8. HomePod mini pair → FLAG as ambiguous, retain both (conflicting attributes = distinct SKUs).
D9. R-DOM-005 dropped — repair_status census proved no variants exist.
D11. Contract dtypes are human aliases; engine resolves via DTYPE_ALIASES
     (e.g. datetime64 -> datetime64[ns]). Contract unchanged by engine bugs.
D12. Unpinned pandas drifted us onto 3.x (unit-less datetime64 astype now a
     hard error). requirements.lock exists — all runs must use it.
D16. Audit metrics must be unit-consistent across before/after (rows, not
     groups). v1 scorecard compared rows (raw) vs groups (clean) for DUP
     checks; caught on first run, views corrected, scorecard regenerated
     without reload. Lesson: a verdict can be right for the wrong reason.
D17. unaccounted=0 proves internal consistency, not correctness: v1 clean-side
     DUP counts used groups where raw used rows, and flagged==after made the
     two wrong numbers agree with each other. Fix: unit-consistent row counts
     + automated three-way crosscheck (profiler <-> MySQL raw <-> clean).
     Also: rerunning a runner is not deploying a fix -- the artifact it
     executes must contain the change.
D18. dim_date is materialized: calendar span exceeds MySQL default
     cte_max_recursion_depth (1000); a CTE view would fail at query time.
D19. Fact views expose contract flags — exclusion is the analyst's one-filter
     decision at query time, never a pre-deletion in the pipeline.
D20. Excel recipe: sales loads to Data Model (worksheet ceiling 1,048,576 vs 1,040,200 rows = 8,376 headroom); dims/audit/reconciliation to worksheets. D21. PQ recipe is a portability demonstration; Python engine is source of truth.
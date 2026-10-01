# Assumptions - written before profiling, adjudicated by evidence

Each assumption was logged before Phase 2 ran. The profiler adjudicated
every one against data - none were silently assumed. Evidence:
reports/findings.csv (96 checks, 6 findings) and reports/damage_report.html.

| ID | Assumption (as written before profiling) | Verdict |
|----|------------------------------------------|---------|
| A1 | PKs are unique and non-null in all 5 tables | CONFIRMED |
| A2 | sales.product_id -> products, sales.store_id -> stores: no orphans | CONFIRMED |
| A3 | products.Category_ID -> category: no orphans | CONFIRMED |
| A4 | warranty.sale_id -> sales: no orphans (every claim traces to a sale) | CONFIRMED |
| A5 | sale_date >= launch_date (no pre-launch sales) | VIOLATED - 493,143 rows (TIME-01) |
| A6 | claim_date >= sale_date (no claims before purchase) | VIOLATED - 2,687 rows (TIME-02) |
| A7 | quantity >= 1 integer; price > 0 numeric | CONFIRMED (quantity census 1-10; all prices parse, all > 0) |
| A8 | Dates parse as valid dates; no future dates | CONFIRMED (per-source formats: sales DD-MM-YYYY, warranty/products ISO) |
| A9 | repair_status is a small, consistent set of labels | CONFIRMED - exactly 4 canonical labels |
| A10 | No meaningful nulls in business columns | CONFIRMED |

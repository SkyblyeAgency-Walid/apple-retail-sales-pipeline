A1. PKs are unique & non-null in all 5 tables.
A2. sales.product_id → products, sales.store_id → stores: no orphans.
A3. products.Category_ID → category: no orphans.
A4. warranty.sale_id → sales: no orphans (every claim traces to a sale).
A5. sale_date >= products.Launch_Date (no pre-launch sales).
A6. claim_date >= sale_date (no claims before purchase).
A7. quantity >= 1 integer; Price > 0 numeric.
A8. Dates parse as valid dates; no future dates.
A9. repair_status is a small, consistent set of labels.
A10. No meaningful nulls in business columns.

| ID | Assumption | Verdict |
|---|---|---|
| A1 | PKs unique & non-null | ✅ CONFIRMED |
| A2–A4 | No FK orphans (all 4 joins) | ✅ CONFIRMED |
| A5 | `sale_date ≥ launch_date` | ❌ **VIOLATED — 493,143 rows** |
| A6 | `claim_date ≥ sale_date` | ❌ **VIOLATED — 2,687 rows** |
| A7 | quantity ≥ 1; price > 0 | ✅ CONFIRMED (1–10; all parse) |
| A8 | Dates parse; none future | ✅ CONFIRMED (per-source formats) |
| A9 | `repair_status` small consistent set | ✅ CONFIRMED — exactly 4 labels |
| A10 | No meaningful nulls | ✅ CONFIRMED |


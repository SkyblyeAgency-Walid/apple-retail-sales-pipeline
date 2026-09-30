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
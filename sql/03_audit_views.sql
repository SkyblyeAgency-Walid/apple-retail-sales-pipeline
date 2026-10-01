CREATE OR REPLACE VIEW apple_raw.vw_audit AS
SELECT 'ID-01' AS check_id, 'PK null/empty: sales.sale_id' AS check_name,
       SUM(sale_id IS NULL OR sale_id = '') AS violations, 0 AS flagged
FROM apple_raw.sales
UNION ALL
SELECT 'ID-02', 'PK duplicate: sales.sale_id', COUNT(*), 0
FROM (SELECT sale_id FROM apple_raw.sales
      GROUP BY sale_id HAVING COUNT(*) > 1) d
UNION ALL
SELECT 'FK-01', 'orphan sales.product_id -> products', COUNT(*), 0
FROM apple_raw.sales s
LEFT JOIN apple_raw.products p ON s.product_id = p.Product_ID
WHERE p.Product_ID IS NULL
UNION ALL
SELECT 'FK-02', 'orphan sales.store_id -> stores', COUNT(*), 0
FROM apple_raw.sales s
LEFT JOIN apple_raw.stores st ON s.store_id = st.Store_ID
WHERE st.Store_ID IS NULL
UNION ALL
SELECT 'FK-03', 'orphan products.Category_ID -> category', COUNT(*), 0
FROM apple_raw.products p
LEFT JOIN apple_raw.category c ON p.Category_ID = c.category_id
WHERE c.category_id IS NULL
UNION ALL
SELECT 'FK-04', 'orphan warranty.sale_id -> sales', COUNT(*), 0
FROM apple_raw.warranty w
LEFT JOIN apple_raw.sales s ON w.sale_id = s.sale_id
WHERE s.sale_id IS NULL
UNION ALL
SELECT 'DOM-01', 'quantity non-numeric / <= 0', COUNT(*), 0
FROM apple_raw.sales
WHERE quantity NOT REGEXP '^[0-9]+$' OR CAST(quantity AS UNSIGNED) <= 0
UNION ALL
SELECT 'DOM-02', 'repair_status outside canonical 4', COUNT(*), 0
FROM apple_raw.warranty
WHERE repair_status NOT IN ('Completed','Pending','In Progress','Rejected')
UNION ALL
SELECT 'TIME-01', 'sale before product launch', COUNT(*), 0
FROM apple_raw.sales s
JOIN apple_raw.products p ON s.product_id = p.Product_ID
WHERE STR_TO_DATE(s.sale_date, '%d-%m-%Y')
    < STR_TO_DATE(p.Launch_Date, '%Y-%m-%d')
UNION ALL
-- NB: format specifiers differ per source column BY DESIGN:
-- claim_date is ISO (%Y-%m-%d), sale_date is day-first (%d-%m-%Y) --
-- proven by the profiler's date-format census, not assumed.
SELECT 'TIME-02', 'claim before sale', COUNT(*), 0
FROM apple_raw.warranty w
JOIN apple_raw.sales s ON w.sale_id = s.sale_id
WHERE STR_TO_DATE(w.claim_date, '%Y-%m-%d')
    < STR_TO_DATE(s.sale_date, '%d-%m-%Y')
UNION ALL
SELECT 'TIME-03', 'sale_date in the future', COUNT(*), 0
FROM apple_raw.sales
WHERE STR_TO_DATE(sale_date, '%d-%m-%Y') > CURDATE()
UNION ALL
-- RAW side counts ROWS in duplicate groups (12 store IDs / 2 product IDs)
SELECT 'DUP-01', 'duplicate stores on name + city', COUNT(*), 0
FROM (SELECT Store_ID FROM apple_raw.stores
      WHERE (Store_Name, City) IN
        (SELECT Store_Name, City FROM apple_raw.stores
         GROUP BY Store_Name, City HAVING COUNT(*) > 1)) d
UNION ALL
SELECT 'DUP-02', 'duplicate products on name', COUNT(*), 0
FROM (SELECT Product_ID FROM apple_raw.products
      WHERE Product_Name IN
        (SELECT Product_Name FROM apple_raw.products
         GROUP BY Product_Name HAVING COUNT(*) > 1)) d;

-- ---------------------------------------------------------------------------
-- Clean view. Same checks on typed data. flagged = rows carrying the
-- contract's flag column; unaccounted = violations - flagged (computed in
-- the scorecard) must be 0 for every check.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW apple_clean.vw_audit AS
SELECT 'ID-01' AS check_id, 'PK null/empty: sales.sale_id' AS check_name,
       SUM(sale_id IS NULL OR sale_id = '') AS violations, 0 AS flagged
FROM apple_clean.sales
UNION ALL
SELECT 'ID-02', 'PK duplicate: sales.sale_id', COUNT(*), 0
FROM (SELECT sale_id FROM apple_clean.sales
      GROUP BY sale_id HAVING COUNT(*) > 1) d
UNION ALL
SELECT 'FK-01', 'orphan sales.product_id -> products', COUNT(*), 0
FROM apple_clean.sales s
LEFT JOIN apple_clean.products p ON s.product_id = p.product_id
WHERE p.product_id IS NULL
UNION ALL
SELECT 'FK-02', 'orphan sales.store_id -> stores', COUNT(*), 0
FROM apple_clean.sales s
LEFT JOIN apple_clean.stores st ON s.store_id = st.store_id
WHERE st.store_id IS NULL
UNION ALL
SELECT 'FK-03', 'orphan products.category_id -> category', COUNT(*), 0
FROM apple_clean.products p
LEFT JOIN apple_clean.category c ON p.category_id = c.category_id
WHERE c.category_id IS NULL
UNION ALL
SELECT 'FK-04', 'orphan warranty.sale_id -> sales', COUNT(*), 0
FROM apple_clean.warranty w
LEFT JOIN apple_clean.sales s ON w.sale_id = s.sale_id
WHERE s.sale_id IS NULL
UNION ALL
SELECT 'DOM-01', 'quantity <= 0', COUNT(*), 0
FROM apple_clean.sales WHERE quantity <= 0
UNION ALL
SELECT 'DOM-02', 'repair_status outside canonical 4', COUNT(*), 0
FROM apple_clean.warranty
WHERE repair_status NOT IN ('Completed','Pending','In Progress','Rejected')
UNION ALL
SELECT 'TIME-01', 'sale before product launch',
       SUM(s.sale_date < p.launch_date), SUM(s.is_pre_launch_sale)
FROM apple_clean.sales s
JOIN apple_clean.products p ON s.product_id = p.product_id
UNION ALL
SELECT 'TIME-02', 'claim before sale',
       SUM(w.claim_date < s.sale_date), SUM(w.is_claim_before_sale)
FROM apple_clean.warranty w
JOIN apple_clean.sales s ON w.sale_id = s.sale_id
UNION ALL
SELECT 'TIME-03', 'sale_date in the future',
       SUM(sale_date > CURDATE()), 0
FROM apple_clean.sales
UNION ALL

SELECT 'DUP-01', 'duplicate stores on name + city',
       SUM(CASE WHEN cnt > 1 THEN cnt ELSE 0 END),
       SUM(CASE WHEN cnt > 1 AND grp_flag = 1 THEN cnt ELSE 0 END)
FROM (SELECT store_name, city, COUNT(*) AS cnt,
             MAX(is_suspected_duplicate_store) AS grp_flag
      FROM apple_clean.stores
      GROUP BY store_name, city) g
UNION ALL
SELECT 'DUP-02', 'duplicate products on name',
       SUM(CASE WHEN cnt > 1 THEN cnt ELSE 0 END),
       SUM(CASE WHEN cnt > 1 AND grp_flag = 1 THEN cnt ELSE 0 END)
FROM (SELECT product_name, COUNT(*) AS cnt,
             MAX(is_ambiguous_product_name) AS grp_flag
      FROM apple_clean.products
      GROUP BY product_name) g;

-- The money query (also executed by src.load_mysql.scorecard, which writes
-- reports/audit_scorecard.csv and validates unaccounted == 0):
SELECT r.check_id, r.check_name,
       r.violations AS before_clean,
       c.violations AS after_clean,
       c.flagged    AS flagged_after,
       c.violations - c.flagged AS unaccounted
FROM apple_raw.vw_audit r
JOIN apple_clean.vw_audit c USING (check_id)
ORDER BY unaccounted DESC, before_clean DESC;
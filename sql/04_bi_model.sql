-- BI layer: conformed dimensions + fact views over apple_clean.
USE apple_clean;

-- 1) dim_date — materialized (recursive CTE depth limit: default 1000 < calendar span)
SET SESSION cte_max_recursion_depth = 100000;

DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date (
  date_key   INT          NOT NULL PRIMARY KEY,   -- YYYYMMDD
  full_date  DATE         NOT NULL UNIQUE,
  year       SMALLINT     NOT NULL,
  quarter    TINYINT      NOT NULL,
  month      TINYINT      NOT NULL,
  month_name VARCHAR(16)  NOT NULL,
  day        TINYINT      NOT NULL,
  weekday_name VARCHAR(16) NOT NULL,
  is_weekend TINYINT      NOT NULL
);

INSERT INTO dim_date
WITH RECURSIVE cal AS (
  SELECT (SELECT MIN(d) FROM (
            SELECT MIN(launch_date) d FROM products
            UNION ALL SELECT MIN(sale_date) FROM sales
            UNION ALL SELECT MIN(claim_date) FROM warranty) a) AS d
  UNION ALL
  SELECT d + INTERVAL 1 DAY FROM cal
  WHERE d < (SELECT MAX(d) FROM (
            SELECT MAX(launch_date) d FROM products
            UNION ALL SELECT MAX(sale_date) FROM sales
            UNION ALL SELECT MAX(claim_date) FROM warranty) b)
)
SELECT YEAR(d)*10000 + MONTH(d)*100 + DAY(d),
       d, YEAR(d), QUARTER(d), MONTH(d), MONTHNAME(d),
       DAY(d), DAYNAME(d), IF(DAYOFWEEK(d) IN (1,7), 1, 0)
FROM cal;

-- 2) Fact view: sales + revenue (the number BI will query)
CREATE OR REPLACE VIEW vw_sales_revenue AS
SELECT s.sale_id,
       s.sale_date,
       d.year, d.quarter, d.month, d.month_name, d.weekday_name,
       st.store_id, st.store_name, st.city, st.country,
       c.category_id, c.category_name,
       p.product_id, p.product_name, p.price,
       s.quantity,
       (s.quantity * p.price) AS revenue,
       s.is_pre_launch_sale
FROM sales s
JOIN products p        ON s.product_id = p.product_id
JOIN category c        ON p.category_id = c.category_id
JOIN stores st         ON s.store_id = st.store_id
LEFT JOIN dim_date d   ON d.full_date = s.sale_date;

-- 3) Fact view: warranty performance
CREATE OR REPLACE VIEW vw_warranty_performance AS
SELECT w.claim_id,
       w.claim_date,
       w.repair_status,
       s.sale_id, s.sale_date,
       DATEDIFF(w.claim_date, s.sale_date) AS days_to_claim,
       st.store_name, st.city, st.country,
       p.product_name, c.category_name,
       w.is_claim_before_sale
FROM warranty w
JOIN sales s           ON w.sale_id = s.sale_id
JOIN products p        ON s.product_id = p.product_id
JOIN category c        ON p.category_id = c.category_id
JOIN stores st         ON s.store_id = st.store_id;
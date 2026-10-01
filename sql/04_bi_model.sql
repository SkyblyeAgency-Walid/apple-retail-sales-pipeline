SET SESSION cte_max_recursion_depth = 100000;

DROP TABLE IF EXISTS apple_clean.dim_date;
CREATE TABLE apple_clean.dim_date (
  date_key     INT         NOT NULL PRIMARY KEY,   -- YYYYMMDD
  full_date    DATE        NOT NULL UNIQUE,
  year         SMALLINT    NOT NULL,
  quarter      TINYINT     NOT NULL,
  month        TINYINT     NOT NULL,
  month_name   VARCHAR(16) NOT NULL,
  day          TINYINT     NOT NULL,
  weekday_name VARCHAR(16) NOT NULL,
  is_weekend   TINYINT     NOT NULL
);

INSERT INTO apple_clean.dim_date
WITH RECURSIVE cal AS (
  SELECT (SELECT MIN(d) FROM (
            SELECT MIN(launch_date) AS d FROM apple_clean.products
            UNION ALL SELECT MIN(sale_date)  FROM apple_clean.sales
            UNION ALL SELECT MIN(claim_date) FROM apple_clean.warranty) lo) AS d
  UNION ALL
  SELECT d + INTERVAL 1 DAY FROM cal
  WHERE d < (SELECT MAX(d) FROM (
            SELECT MAX(launch_date) AS d FROM apple_clean.products
            UNION ALL SELECT MAX(sale_date)  FROM apple_clean.sales
            UNION ALL SELECT MAX(claim_date) FROM apple_clean.warranty) hi)
)
SELECT YEAR(d) * 10000 + MONTH(d) * 100 + DAY(d),
       d,
       YEAR(d), QUARTER(d), MONTH(d), MONTHNAME(d),
       DAY(d), DAYNAME(d),
       IF(DAYOFWEEK(d) IN (1, 7), 1, 0)
FROM cal;

CREATE OR REPLACE VIEW apple_clean.vw_sales_revenue AS
SELECT s.sale_id,
       s.sale_date,
       d.year, d.quarter, d.month, d.month_name, d.weekday_name, d.is_weekend,
       st.store_id, st.store_name, st.city, st.country,
       c.category_id, c.category_name,
       p.product_id, p.product_name, p.price,
       s.quantity,
       CAST(s.quantity * p.price AS DECIMAL(18, 2)) AS revenue,
       s.is_pre_launch_sale
FROM apple_clean.sales s
JOIN apple_clean.products p ON s.product_id = p.product_id
JOIN apple_clean.category c ON p.category_id = c.category_id
JOIN apple_clean.stores st  ON s.store_id  = st.store_id
LEFT JOIN apple_clean.dim_date d ON d.full_date = s.sale_date;

CREATE OR REPLACE VIEW apple_clean.vw_warranty_performance AS
SELECT w.claim_id,
       w.claim_date,
       w.repair_status,
       s.sale_id, s.sale_date,
       DATEDIFF(w.claim_date, s.sale_date) AS days_to_claim,
       st.store_name, st.city, st.country,
       p.product_name, c.category_name,
       w.is_claim_before_sale
FROM apple_clean.warranty w
JOIN apple_clean.sales s    ON w.sale_id     = s.sale_id
JOIN apple_clean.products p ON s.product_id  = p.product_id
JOIN apple_clean.category c ON p.category_id = c.category_id
JOIN apple_clean.stores st  ON s.store_id    = st.store_id;
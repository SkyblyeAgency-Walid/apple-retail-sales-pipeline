CREATE SCHEMA IF NOT EXISTS apple_clean;

CREATE TABLE IF NOT EXISTS apple_clean.category (
  category_id   VARCHAR(32)  NOT NULL,
  category_name VARCHAR(255) NOT NULL,
  PRIMARY KEY (category_id)
);

CREATE TABLE IF NOT EXISTS apple_clean.stores (
  store_id   VARCHAR(32)  NOT NULL,
  store_name VARCHAR(255) NOT NULL,
  city       VARCHAR(255) NOT NULL,
  country    VARCHAR(64)  NOT NULL,
  is_suspected_duplicate_store TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (store_id),
  CONSTRAINT chk_store_flag CHECK (is_suspected_duplicate_store IN (0,1))
);

CREATE TABLE IF NOT EXISTS apple_clean.products (
  product_id   VARCHAR(32)   NOT NULL,
  product_name VARCHAR(255)  NOT NULL,
  category_id  VARCHAR(32)   NOT NULL,
  launch_date  DATE          NOT NULL,
  price        DECIMAL(12,2) NOT NULL,
  is_ambiguous_product_name  TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (product_id),
  KEY ix_products_category (category_id),
  CONSTRAINT fk_products_category FOREIGN KEY (category_id)
    REFERENCES apple_clean.category (category_id),
  CONSTRAINT chk_price_positive CHECK (price > 0),
  CONSTRAINT chk_product_flag CHECK (is_ambiguous_product_name IN (0,1))
);

CREATE TABLE IF NOT EXISTS apple_clean.sales (
  sale_id    VARCHAR(32) NOT NULL,
  sale_date  DATE        NOT NULL,
  store_id   VARCHAR(32) NOT NULL,
  product_id VARCHAR(32) NOT NULL,
  quantity   SMALLINT UNSIGNED NOT NULL,
  is_pre_launch_sale TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (sale_id),
  KEY ix_sales_store (store_id),
  KEY ix_sales_product (product_id),
  KEY ix_sales_date (sale_date),
  CONSTRAINT fk_sales_store FOREIGN KEY (store_id)
    REFERENCES apple_clean.stores (store_id),
  CONSTRAINT fk_sales_product FOREIGN KEY (product_id)
    REFERENCES apple_clean.products (product_id),
  CONSTRAINT chk_quantity_positive CHECK (quantity >= 1),
  CONSTRAINT chk_sales_flag CHECK (is_pre_launch_sale IN (0,1))
);

CREATE TABLE IF NOT EXISTS apple_clean.warranty (
  claim_id      VARCHAR(32) NOT NULL,
  claim_date    DATE        NOT NULL,
  sale_id       VARCHAR(32) NOT NULL,
  repair_status VARCHAR(32) NOT NULL,
  is_claim_before_sale TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (claim_id),
  KEY ix_warranty_sale (sale_id),
  CONSTRAINT fk_warranty_sale FOREIGN KEY (sale_id)
    REFERENCES apple_clean.sales (sale_id),
  CONSTRAINT chk_repair_status
    CHECK (repair_status IN ('Completed','Pending','In Progress','Rejected')),
  CONSTRAINT chk_warranty_flag CHECK (is_claim_before_sale IN (0,1))
);
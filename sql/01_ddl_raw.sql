CREATE SCHEMA IF NOT EXISTS apple_raw;

CREATE TABLE IF NOT EXISTS apple_raw.category (
  category_id   VARCHAR(32),
  category_name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS apple_raw.products (
  Product_ID   VARCHAR(32),
  Product_Name VARCHAR(255),
  Category_ID  VARCHAR(32),
  Launch_Date  VARCHAR(10),
  Price        VARCHAR(16)
);

CREATE TABLE IF NOT EXISTS apple_raw.sales (
  sale_id    VARCHAR(32),
  sale_date  VARCHAR(10),
  store_id   VARCHAR(32),
  product_id VARCHAR(32),
  quantity   VARCHAR(8)
);

CREATE TABLE IF NOT EXISTS apple_raw.stores (
  Store_ID   VARCHAR(32),
  Store_Name VARCHAR(255),
  City       VARCHAR(255),
  Country    VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS apple_raw.warranty (
  claim_id      VARCHAR(32),
  claim_date    VARCHAR(10),
  sale_id       VARCHAR(32),
  repair_status VARCHAR(32)
);
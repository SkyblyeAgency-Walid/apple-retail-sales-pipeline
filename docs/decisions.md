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
let
    fk1 = Table.RowCount(Table.NestedJoin(clean_sales, {"product_id"},
             clean_products, {"product_id"}, "m", JoinKind.LeftAnti)),
    fk2 = Table.RowCount(Table.NestedJoin(clean_sales, {"store_id"},
             clean_stores, {"store_id"}, "m", JoinKind.LeftAnti)),
    fk3 = Table.RowCount(Table.NestedJoin(clean_products, {"category_id"},
             clean_category, {"category_id"}, "m", JoinKind.LeftAnti)),
    fk4 = Table.RowCount(Table.NestedJoin(clean_warranty, {"sale_id"},
             clean_sales, {"sale_id"}, "m", JoinKind.LeftAnti)),
    Result = Table.FromRecords({
        [check_id = "FK-01", check = "orphan sales->products",       violations = fk1],
        [check_id = "FK-02", check = "orphan sales->stores",         violations = fk2],
        [check_id = "FK-03", check = "orphan products->category",    violations = fk3],
        [check_id = "FK-04", check = "orphan warranty->sales",       violations = fk4]})
in
    Result
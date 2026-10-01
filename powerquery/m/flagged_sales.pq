let
    Source = clean_sales,
    Products = Table.Buffer(clean_products),
    MergedP = Table.NestedJoin(Source, {"product_id"}, Products,
        {"product_id"}, "p", JoinKind.LeftOuter),
    ExpandedP = Table.ExpandTableColumn(MergedP, "p",
        {"product_name", "category_id", "launch_date", "price"}),
    Categories = Table.Buffer(clean_category),
    MergedC = Table.NestedJoin(ExpandedP, {"category_id"}, Categories,
        {"category_id"}, "c", JoinKind.LeftOuter),
    ExpandedC = Table.ExpandTableColumn(MergedC, "c", {"category_name"}),
    Flagged = Table.AddColumn(ExpandedC, "is_pre_launch_sale",
        each if [sale_date] < [launch_date] then 1 else 0, Int32.Type),
    Revenue = Table.AddColumn(Flagged, "revenue",
        each [quantity] * [price], type number),
    Final = Table.SelectColumns(Revenue,
        {"sale_id", "sale_date", "store_id", "product_id", "product_name",
         "category_name", "quantity", "price", "revenue",
         "is_pre_launch_sale"})
in
    Final
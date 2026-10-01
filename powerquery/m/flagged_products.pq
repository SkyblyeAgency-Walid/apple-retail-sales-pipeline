let
    Source = clean_products,
    Grouped = Table.Group(Source, {"product_name"},
        {{"cnt", each Table.RowCount(_), Int32.Type}}),
    Dupes = Table.SelectRows(Grouped, each [cnt] > 1),
    Merged = Table.NestedJoin(Source, {"product_name"}, Dupes,
        {"product_name"}, "d", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Merged, "d", {"cnt"}),
    Flagged = Table.AddColumn(Expanded, "is_ambiguous_product_name",
        each if [cnt] = null then 0 else 1, Int32.Type),
    Final = Table.SelectColumns(Flagged,
        {"product_id", "product_name", "category_id", "launch_date", "price",
         "is_ambiguous_product_name"})
in
    Final
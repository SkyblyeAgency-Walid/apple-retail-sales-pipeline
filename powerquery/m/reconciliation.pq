let
    RawQty = Table.AddColumn(stg_sales, "q",
        each try Number.FromText([quantity]) otherwise null, type nullable number),
    RawPrice = Table.AddColumn(stg_products, "p",
        each try Number.FromText([Price]) otherwise null, type nullable number),
    PriceLookup = Table.SelectColumns(RawPrice, {"Product_ID", "p"}),
    Joined = Table.NestedJoin(RawQty, {"product_id"}, PriceLookup,
        {"Product_ID"}, "j", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "j", {"p"}),
    RevRows = Table.AddColumn(Expanded, "rev",
        each if [p] = null or [q] = null then null else [q] * [p],
        type nullable number),
    Result = Table.FromRecords({
        [metric = "rows",    raw = Table.RowCount(stg_sales),
                             clean = Table.RowCount(clean_sales)],
        [metric = "units",   raw = List.Sum(RawQty[q]),
                             clean = List.Sum(clean_sales[quantity])],
        [metric = "revenue", raw = List.Sum(RevRows[rev]),
                             clean = List.Sum(flagged_sales[revenue])]}),
    WithVar = Table.AddColumn(Result, "variance", each [raw] - [clean])
in
    WithVar
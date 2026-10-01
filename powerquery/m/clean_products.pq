let
    Source = stg_products,
    Trimmed = Table.TransformColumns(Source, {},
        each if _ is text then Text.Trim(_) else _),
    Renamed = Table.RenameColumns(Trimmed, {
        {"Product_ID", "product_id"}, {"Product_Name", "product_name"},
        {"Category_ID", "category_id"}, {"Launch_Date", "launch_date"},
        {"Price", "price"}}),
    ParsedLaunch = Table.AddColumn(Renamed, "launch_date_new",
        each fnCleanISODate([launch_date]), type nullable date),
    ParsedPrice = Table.AddColumn(ParsedLaunch, "price_new",
        each try Number.FromText([price]) otherwise null, type nullable number),
    Kept = Table.SelectRows(ParsedPrice,
        each [launch_date_new] <> null and [price_new] <> null and [price_new] > 0),
    Typed = Table.TransformColumnTypes(Kept,
        {{"launch_date_new", type date}, {"price_new", type number}}),
    Removed = Table.RemoveColumns(Typed, {"launch_date", "price"}),
    Final = Table.RenameColumns(Removed,
        {{"launch_date_new", "launch_date"}, {"price_new", "price"}})
in
    Final
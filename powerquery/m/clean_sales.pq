let
    Source = stg_sales,
    Trimmed = Table.TransformColumns(Source, {},
        each if _ is text then Text.Trim(_) else _),
    ParsedDate = Table.AddColumn(Trimmed, "sale_date_new",
        each fnCleanSaleDate([sale_date]), type nullable date),
    ParsedQty = Table.AddColumn(ParsedDate, "quantity_new",
        each try Number.FromText([quantity]) otherwise null, type nullable number),
    Kept = Table.SelectRows(ParsedQty,
        each [sale_date_new] <> null and [quantity_new] <> null and [quantity_new] >= 1),
    Typed = Table.TransformColumnTypes(Kept,
        {{"sale_date_new", type date}, {"quantity_new", Int32.Type}}),
    Removed = Table.RemoveColumns(Typed, {"sale_date", "quantity"}),
    Final = Table.RenameColumns(Removed,
        {{"sale_date_new", "sale_date"}, {"quantity_new", "quantity"}})
in
    Final
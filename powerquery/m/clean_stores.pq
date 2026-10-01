let
    Source = stg_stores,
    Trimmed = Table.TransformColumns(Source, {},
        each if _ is text then Text.Trim(_) else _),
    Renamed = Table.RenameColumns(Trimmed, {
        {"Store_ID", "store_id"}, {"Store_Name", "store_name"},
        {"City", "city"}, {"Country", "country"}})
in
    Renamed
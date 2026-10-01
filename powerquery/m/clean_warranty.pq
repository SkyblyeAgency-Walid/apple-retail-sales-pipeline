let
    Source = stg_warranty,
    Trimmed = Table.TransformColumns(Source, {},
        each if _ is text then Text.Trim(_) else _),
    Parsed = Table.AddColumn(Trimmed, "claim_date_new",
        each fnCleanISODate([claim_date]), type nullable date),
    Kept = Table.SelectRows(Parsed, each [claim_date_new] <> null),
    Typed = Table.TransformColumnTypes(Kept, {{"claim_date_new", type date}}),
    Removed = Table.RemoveColumns(Typed, {"claim_date"}),
    Final = Table.RenameColumns(Removed, {{"claim_date_new", "claim_date"}})
in
    Final
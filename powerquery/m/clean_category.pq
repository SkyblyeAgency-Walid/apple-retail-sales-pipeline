let
    Source = stg_category,
    Trimmed = Table.TransformColumns(Source, {},
        each if _ is text then Text.Trim(_) else _)
in
    Trimmed
let
    Source = clean_warranty,
    Merged = Table.NestedJoin(Source, {"sale_id"}, clean_sales, {"sale_id"},
        "s", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Merged, "s", {"sale_date"}),
    Flagged = Table.AddColumn(Expanded, "is_claim_before_sale",
        each if [claim_date] < [sale_date] then 1 else 0, Int32.Type),
    Final = Table.SelectColumns(Flagged,
        {"claim_id", "claim_date", "sale_id", "repair_status", "sale_date",
         "is_claim_before_sale"})
in
    Final
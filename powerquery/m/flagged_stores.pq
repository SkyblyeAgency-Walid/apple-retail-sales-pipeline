let
    Source = clean_stores,
    Grouped = Table.Group(Source, {"store_name", "city"},
        {{"cnt", each Table.RowCount(_), Int32.Type}}),
    Dupes = Table.SelectRows(Grouped, each [cnt] > 1),
    Merged = Table.NestedJoin(Source, {"store_name", "city"}, Dupes,
        {"store_name", "city"}, "d", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Merged, "d", {"cnt"}),
    Flagged = Table.AddColumn(Expanded, "is_suspected_duplicate_store",
        each if [cnt] = null then 0 else 1, Int32.Type),
    Final = Table.SelectColumns(Flagged,
        {"store_id", "store_name", "city", "country",
         "is_suspected_duplicate_store"})
in
    Final
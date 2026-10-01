let
    Source = Csv.Document(File.Contents(pSourceFolder & "\sales.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    AllText = Table.TransformColumnTypes(Promoted,
        {{"sale_id", type text}, {"sale_date", type text},
         {"store_id", type text}, {"product_id", type text},
         {"quantity", type text}})
in
    AllText
let
    Source = Csv.Document(File.Contents(pSourceFolder & "\warranty.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    AllText = Table.TransformColumnTypes(Promoted,
        {{"claim_id", type text}, {"claim_date", type text},
         {"sale_id", type text}, {"repair_status", type text}})
in
    AllText
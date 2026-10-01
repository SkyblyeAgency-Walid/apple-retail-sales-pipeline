let
    Source = Csv.Document(File.Contents(pSourceFolder & "\stores.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    AllText = Table.TransformColumnTypes(Promoted,
        {{"Store_ID", type text}, {"Store_Name", type text},
         {"City", type text}, {"Country", type text}})
in
    AllText
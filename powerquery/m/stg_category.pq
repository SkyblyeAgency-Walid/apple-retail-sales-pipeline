let
    Source = Csv.Document(File.Contents(pSourceFolder & "\category.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    AllText = Table.TransformColumnTypes(Promoted,
        {{"category_id", type text}, {"category_name", type text}})
in
    AllText
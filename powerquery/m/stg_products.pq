let
    Source = Csv.Document(File.Contents(pSourceFolder & "\products.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    AllText = Table.TransformColumnTypes(Promoted,
        {{"Product_ID", type text}, {"Product_Name", type text},
         {"Category_ID", type text}, {"Launch_Date", type text},
         {"Price", type text}})
in
    AllText
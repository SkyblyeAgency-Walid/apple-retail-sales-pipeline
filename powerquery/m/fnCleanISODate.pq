(textInput as nullable text) as nullable date =>
    if textInput = null then null
    else
        try #date(
            Number.FromText(Text.Start(textInput, 4)),
            Number.FromText(Text.Middle(textInput, 5, 2)),
            Number.FromText(Text.End(textInput, 2)))
        otherwise null
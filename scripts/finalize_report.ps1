param(
    [string]$DocPath = "D:\Ryan Project 2026\fuel-price-predictor\docs\Ryan_Final_Project_Report.docx"
)

Add-Type -AssemblyName Microsoft.Office.Interop.Word

function Find-RangeByToken {
    param(
        $Document,
        [string]$Token
    )

    $range = $Document.Content.Duplicate
    $find = $range.Find
    $find.ClearFormatting()
    $find.Text = $Token
    $find.Forward = $true
    $find.Wrap = [Microsoft.Office.Interop.Word.WdFindWrap]::wdFindStop

    if ($find.Execute()) {
        return $range
    }

    return $null
}

function Build-CaptionEntries {
    param(
        $Document,
        [string]$Prefix
    )

    $entries = New-Object System.Collections.Generic.List[string]

    foreach ($paragraph in $Document.Paragraphs) {
        $text = ($paragraph.Range.Text -replace "[`r`a]", "").Trim()
        if ($text -match "^$Prefix\s+\d+\.\d+:") {
            $page = $paragraph.Range.Information([Microsoft.Office.Interop.Word.WdInformation]::wdActiveEndAdjustedPageNumber)
            $entries.Add("$text`t$page")
        }
    }

    return $entries
}

function Build-HeadingEntries {
    param(
        $Document
    )

    $entries = New-Object System.Collections.Generic.List[string]

    foreach ($paragraph in $Document.Paragraphs) {
        $text = ($paragraph.Range.Text -replace "[`r`a]", "").Trim()
        if (-not $text) {
            continue
        }

        $styleName = $paragraph.Range.Style.NameLocal
        if ($styleName -notmatch "^Heading [1-3]$") {
            continue
        }

        $page = $paragraph.Range.Information([Microsoft.Office.Interop.Word.WdInformation]::wdActiveEndAdjustedPageNumber)
        if (($page -gt 1) -and ($page -le 4)) {
            $page = $page - 1
        }

        if ($styleName -eq "Heading 1") {
            $entries.Add("$text`t$page")
        }
        elseif ($styleName -eq "Heading 2") {
            $entries.Add("    $text`t$page")
        }
        else {
            $entries.Add("        $text`t$page")
        }
    }

    return $entries
}

function Format-EntryRange {
    param($Range)

    $Range.Font.Name = "Times New Roman"
    $Range.Font.Size = 11
    $Range.ParagraphFormat.Alignment = [Microsoft.Office.Interop.Word.WdParagraphAlignment]::wdAlignParagraphLeft
    $Range.ParagraphFormat.LineSpacingRule = [Microsoft.Office.Interop.Word.WdLineSpacing]::wdLineSpaceSingle
    $Range.ParagraphFormat.TabStops.ClearAll()
    $Range.ParagraphFormat.TabStops.Add($word.CentimetersToPoints(15.2), [Microsoft.Office.Interop.Word.WdTabAlignment]::wdAlignTabRight, [Microsoft.Office.Interop.Word.WdTabLeader]::wdTabLeaderDots) | Out-Null
}

function Replace-TokenWithLines {
    param(
        $Document,
        [string]$Token,
        [System.Collections.Generic.List[string]]$Lines
    )

    $range = Find-RangeByToken -Document $Document -Token $Token
    if (-not $range) {
        return
    }

    $range.Text = ""
    foreach ($line in $Lines) {
        $range.InsertAfter("$line`r")
    }

    Format-EntryRange -Range $range
}

function Find-ParagraphRangeByText {
    param(
        $Document,
        [string]$HeadingText
    )

    foreach ($paragraph in $Document.Paragraphs) {
        $text = ($paragraph.Range.Text -replace "[`r`a]", "").Trim()
        if ($text -eq $HeadingText) {
            return $paragraph.Range
        }
    }

    return $null
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    $doc = $word.Documents.Open($DocPath)

    $doc.Repaginate()
    $tocEntries = Build-HeadingEntries -Document $doc
    $tableEntries = Build-CaptionEntries -Document $doc -Prefix "Table"
    $figureEntries = Build-CaptionEntries -Document $doc -Prefix "Figure"

    Replace-TokenWithLines -Document $doc -Token "[[TOC]]" -Lines $tocEntries
    Replace-TokenWithLines -Document $doc -Token "[[LIST_TABLES]]" -Lines $tableEntries
    Replace-TokenWithLines -Document $doc -Token "[[LIST_FIGURES]]" -Lines $figureEntries

    $doc.Repaginate()
    $sections = $doc.Sections
    $footerIndexes = @(
        [Microsoft.Office.Interop.Word.WdHeaderFooterIndex]::wdHeaderFooterPrimary,
        [Microsoft.Office.Interop.Word.WdHeaderFooterIndex]::wdHeaderFooterFirstPage,
        [Microsoft.Office.Interop.Word.WdHeaderFooterIndex]::wdHeaderFooterEvenPages
    )

    for ($i = 1; $i -le $sections.Count; $i++) {
        $section = $sections.Item($i)
        $section.PageSetup.DifferentFirstPageHeaderFooter = $false

        foreach ($footerIndex in $footerIndexes) {
            $sectionFooter = $section.Footers.Item($footerIndex)
            $sectionFooter.LinkToPrevious = $false
            $sectionFooter.Range.Text = ""
            $sectionFooter.Range.ParagraphFormat.Alignment = [Microsoft.Office.Interop.Word.WdParagraphAlignment]::wdAlignParagraphCenter
        }

        if ($i -eq 1) {
            continue
        }

        $footer = $section.Footers.Item([Microsoft.Office.Interop.Word.WdHeaderFooterIndex]::wdHeaderFooterPrimary)
        $footer.Range.Text = ""
        $footer.Range.ParagraphFormat.Alignment = [Microsoft.Office.Interop.Word.WdParagraphAlignment]::wdAlignParagraphCenter

        if ($i -eq 2) {
            $footer.PageNumbers.RestartNumberingAtSection = $true
            $footer.PageNumbers.StartingNumber = 2
            $footer.PageNumbers.NumberStyle = [Microsoft.Office.Interop.Word.WdPageNumberStyle]::wdPageNumberStyleArabic
            $fieldSwitch = "Arabic"
        }
        else {
            $footer.PageNumbers.RestartNumberingAtSection = $false
            $footer.PageNumbers.NumberStyle = [Microsoft.Office.Interop.Word.WdPageNumberStyle]::wdPageNumberStyleArabic
            $fieldSwitch = "Arabic"
        }

        $fieldRange = $footer.Range
        $fieldRange.Collapse([Microsoft.Office.Interop.Word.WdCollapseDirection]::wdCollapseStart)
        $field = $footer.Range.Fields.Add($fieldRange, [Microsoft.Office.Interop.Word.WdFieldType]::wdFieldEmpty, "PAGE \* $fieldSwitch", $true)
        $field.Update() | Out-Null
        $footer.Range.ParagraphFormat.Alignment = [Microsoft.Office.Interop.Word.WdParagraphAlignment]::wdAlignParagraphCenter
    }

    $doc.Repaginate()
    $doc.Save()
    $doc.Close()
}
finally {
    $word.Quit()
}

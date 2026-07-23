param(
    [string]$DocPath = (Join-Path $PSScriptRoot "..\docs\Ryan_Final_Project_Report.docx")
)

$resolved = (Resolve-Path $DocPath).Path
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open($resolved)
    foreach ($toc in $document.TablesOfContents) { $toc.Update() }
    $document.Fields.Update() | Out-Null
    $document.Save()
    $pdf = [System.IO.Path]::ChangeExtension($resolved, ".pdf")
    $document.ExportAsFixedFormat($pdf, 17)
    $document.Close($false)
    Write-Output "Updated fields and exported: $pdf"
}
finally {
    $word.Quit()
}

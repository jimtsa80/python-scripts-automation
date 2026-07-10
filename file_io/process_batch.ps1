param(
    [string]$BatchRoot = "F:\downloads\batch20",
    [string]$Recipients = "jimtsarouhas@gmail.com,chandrinos@gmail.com"
)

$scriptDir = $PSScriptRoot
$uploadScript = Join-Path $scriptDir "upload_file.ps1"
$emailScript = Join-Path $scriptDir "send_link_email.ps1"

function Format-Duration([TimeSpan]$ts) {
    if ($ts.TotalHours -ge 1) {
        return "{0:D2}:{1:D2}:{2:D2}" -f [int]$ts.TotalHours, $ts.Minutes, $ts.Seconds
    }
    return "{0:D2}:{1:D2}" -f [int]$ts.TotalMinutes, $ts.Seconds
}

if (-not (Test-Path -LiteralPath $BatchRoot)) {
    Write-Error "Batch root not found: $BatchRoot"
    exit 1
}

$targetFolders = @()
$skipped = @()
foreach ($chi in Get-ChildItem -LiteralPath $BatchRoot -Directory -ErrorAction SilentlyContinue) {
    foreach ($psi in Get-ChildItem -LiteralPath $chi.FullName -Directory -ErrorAction SilentlyContinue) {
        foreach ($zeta in Get-ChildItem -LiteralPath $psi.FullName -Directory -ErrorAction SilentlyContinue) {
            if ($zeta.Name -like "part*") {
                $skipped += $zeta.FullName
                continue
            }
            $targetFolders += $zeta
        }
    }
}

if ($skipped.Count -gt 0) {
    Write-Host "Skipped $($skipped.Count) folder(s) starting with 'part'"
    foreach ($path in $skipped) {
        Write-Host "  - $path"
    }
    Write-Host ""
}

if ($targetFolders.Count -eq 0) {
    Write-Error "No folders found at $BatchRoot\*\*\*"
    exit 1
}

Write-Host "Found $($targetFolders.Count) folder(s) to process under $BatchRoot"
Write-Host ""

$processed = 0
$failed = 0

foreach ($folder in $targetFolders) {
    $folderName = $folder.Name
    $parentPath = $folder.Parent.FullName
    $zipPath = Join-Path $parentPath "$folderName.zip"

    Write-Host "============================================"
    Write-Host "Folder: $($folder.FullName)"
    Write-Host "Zip:    $zipPath"
    Write-Host "============================================"

    Write-Host "Zipping..."
    $zipTimer = [System.Diagnostics.Stopwatch]::StartNew()
    & tar.exe -a -c -f $zipPath -C $parentPath $folderName
    $zipTimer.Stop()

    if (-not (Test-Path -LiteralPath $zipPath)) {
        Write-Host "ERROR: Zip failed for $folderName"
        $failed++
        Write-Host ""
        continue
    }

    $zipSizeMb = [math]::Round((Get-Item -LiteralPath $zipPath).Length / 1MB, 2)
    Write-Host "Zip done in $(Format-Duration $zipTimer.Elapsed) ($zipSizeMb MB)"
    Write-Host ""

    Write-Host "Uploading..."
    $uploadTimer = [System.Diagnostics.Stopwatch]::StartNew()
    $uploadOutput = & powershell.exe -ExecutionPolicy Bypass -File $uploadScript -ZipPath $zipPath 2>&1
    $uploadTimer.Stop()

    foreach ($line in ($uploadOutput | Where-Object { $_ -notmatch '^https?://' })) {
        if ($line) { Write-Host $line }
    }

    $link = ($uploadOutput | Where-Object { $_ -match '^https?://' } | Select-Object -Last 1)
    if (-not $link) {
        Write-Host "ERROR: Upload failed for $folderName"
        $failed++
        Write-Host ""
        continue
    }

    Write-Host "Upload done in $(Format-Duration $uploadTimer.Elapsed)"
    Write-Host "LINK: $link"
    Write-Host ""

    Write-Host "Sending email..."
    & powershell.exe -ExecutionPolicy Bypass -File $emailScript `
        -Link $link `
        -ZipName "$folderName.zip" `
        -Recipients $Recipients

    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Email failed for $folderName.zip"
        $failed++
    }
    else {
        $processed++
    }

    Write-Host ""
}

Write-Host "============================================"
Write-Host "Done. Processed: $processed, Failed: $failed"
Write-Host "============================================"

if ($failed -gt 0) {
    exit 1
}

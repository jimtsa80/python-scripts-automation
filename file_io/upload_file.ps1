param(
    [Parameter(Mandatory = $true)]
    [string]$ZipPath
)

$ErrorActionPreference = "Stop"
$apiBase = "https://storage.to/api"
$tokenFile = Join-Path $PSScriptRoot ".visitor_token"

function Get-VisitorToken {
    if (Test-Path -LiteralPath $tokenFile) {
        return (Get-Content -LiteralPath $tokenFile -Raw).Trim()
    }

    $token = [guid]::NewGuid().ToString()
    Set-Content -LiteralPath $tokenFile -Value $token -NoNewline
    return $token
}

function Upload-Litterbox([string]$Path) {
    $uri = "https://litterbox.catbox.moe/resources/internals/api.php"
    $response = & curl.exe -s `
        -F "reqtype=fileupload" `
        -F "time=72h" `
        -F "fileToUpload=@$Path" `
        $uri

    $link = ($response | Out-String).Trim()
    if ($link -match '^https?://') {
        return $link
    }

    if ($response -match '413|Too Large|Request Entity Too Large') {
        throw "File exceeds litterbox 1 GB limit."
    }

    throw "Litterbox upload failed: $($link.Substring(0, [Math]::Min(200, $link.Length)))"
}

function Upload-StorageTo([string]$Path) {
    $file = Get-Item -LiteralPath $Path
    $visitorToken = Get-VisitorToken
    $headers = @{ "X-Visitor-Token" = $visitorToken }

    $initBody = @{
        filename     = $file.Name
        content_type = "application/zip"
        size         = $file.Length
    } | ConvertTo-Json

    $init = Invoke-RestMethod -Uri "$apiBase/upload/init" -Method Post `
        -ContentType "application/json" -Headers $headers -Body $initBody

    if (-not $init.success) {
        throw "storage.to init failed."
    }

    $ownerHeaders = @{
        "X-Visitor-Token" = $visitorToken
        "Authorization"   = "Owner $($init.owner_token)"
    }

    if ($init.type -eq "single") {
        & curl.exe -sS -X PUT -T $Path $init.upload_url | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "storage.to single upload failed."
        }
    }
    else {
        $partSize = [int64]$init.part_size
        $totalParts = [int]$init.total_parts
        $partUrls = @{}

        foreach ($entry in $init.initial_urls.PSObject.Properties) {
            $partUrls[[int]$entry.Name] = [string]$entry.Value
        }

        $missingParts = 1..$totalParts | Where-Object { -not $partUrls.ContainsKey($_) }
        if ($missingParts.Count -gt 0) {
            $partsBody = @{
                upload_id    = $init.upload_id
                part_numbers = $missingParts
            } | ConvertTo-Json

            $partsResponse = Invoke-RestMethod -Uri "$apiBase/upload/parts" -Method Post `
                -ContentType "application/json" -Headers $ownerHeaders -Body $partsBody

            foreach ($part in $partsResponse.part_urls) {
                $partUrls[[int]$part.partNumber] = [string]$part.url
            }
        }

        $uploadedParts = @()
        $stream = [System.IO.File]::OpenRead($Path)
        try {
            for ($partNumber = 1; $partNumber -le $totalParts; $partNumber++) {
                $offset = ($partNumber - 1) * $partSize
                $length = [Math]::Min($partSize, $file.Length - $offset)
                $tempPart = [System.IO.Path]::GetTempFileName()

                try {
                    $partStream = [System.IO.File]::OpenWrite($tempPart)
                    try {
                        $stream.Seek($offset, [System.IO.SeekOrigin]::Begin) | Out-Null
                        $buffer = New-Object byte[] 81920
                        $remaining = $length
                        while ($remaining -gt 0) {
                            $read = $stream.Read($buffer, 0, [Math]::Min($buffer.Length, $remaining))
                            if ($read -le 0) { break }
                            $partStream.Write($buffer, 0, $read)
                            $remaining -= $read
                        }
                    }
                    finally {
                        $partStream.Close()
                    }

                    $headersFile = [System.IO.Path]::GetTempFileName()
                    try {
                        & curl.exe -sS -D $headersFile -o NUL -X PUT -T $tempPart $partUrls[$partNumber]
                        if ($LASTEXITCODE -ne 0) {
                            throw "storage.to part $partNumber upload failed."
                        }

                        $etag = (Select-String -Path $headersFile -Pattern '^etag:\s*(.+)$' -CaseSensitive:$false |
                            Select-Object -Last 1).Matches[0].Groups[1].Value.Trim()

                        if (-not $etag) {
                            throw "storage.to part $partNumber missing ETag."
                        }

                        $uploadedParts += @{
                            partNumber = $partNumber
                            etag       = $etag
                        }
                    }
                    finally {
                        Remove-Item -LiteralPath $headersFile -Force -ErrorAction SilentlyContinue
                    }
                }
                finally {
                    Remove-Item -LiteralPath $tempPart -Force -ErrorAction SilentlyContinue
                }
            }
        }
        finally {
            $stream.Close()
        }

        $completeBody = @{
            upload_id = $init.upload_id
            parts     = $uploadedParts
        } | ConvertTo-Json -Depth 4

        Invoke-RestMethod -Uri "$apiBase/upload/complete-multipart" -Method Post `
            -ContentType "application/json" -Headers $ownerHeaders -Body $completeBody | Out-Null
    }

    $confirmBody = @{
        filename     = $file.Name
        size         = $file.Length
        content_type = "application/zip"
        r2_key       = $init.r2_key
    } | ConvertTo-Json

    $confirm = Invoke-RestMethod -Uri "$apiBase/upload/confirm" -Method Post `
        -ContentType "application/json" -Headers $headers -Body $confirmBody

    if (-not $confirm.success -or -not $confirm.file.url) {
        throw "storage.to confirm failed."
    }

    return [string]$confirm.file.url
}

if (-not (Test-Path -LiteralPath $ZipPath)) {
    Write-Error "Zip not found: $ZipPath"
    exit 1
}

$fileSize = (Get-Item -LiteralPath $ZipPath).Length
$sizeMb = [math]::Round($fileSize / 1MB, 2)

try {
    if ($fileSize -le 950MB) {
        Write-Output (Upload-Litterbox -Path $ZipPath)
        exit 0
    }

    [Console]::Error.WriteLine("File is $sizeMb MB (>1 GB), using storage.to...")
    Write-Output (Upload-StorageTo -Path $ZipPath)
    exit 0
}
catch {
    Write-Error "Upload failed ($sizeMb MB): $($_.Exception.Message)"
    exit 1
}

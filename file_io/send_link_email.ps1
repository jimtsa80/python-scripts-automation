param(
    [Parameter(Mandatory = $true)]
    [string]$Link,

    [string]$ZipName = "file.zip",

    [string]$Recipients = "jimtsarouhas@gmail.com,chandrinos@gmail.com"
)

$configPath = Join-Path $PSScriptRoot "creds_email.ps1"
if (-not (Test-Path $configPath)) {
    Write-Warning "Email not sent: create creds_email.ps1 (copy from creds_email.ps1.example)."
    exit 1
}

. $configPath

if (-not $SmtpUser -or -not $SmtpPassword) {
    Write-Warning "Email not sent: set `$SmtpUser and `$SmtpPassword in creds_email.ps1"
    exit 1
}

$recipientList = $Recipients -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ }

$body = @"
Download link:
$Link

Download link, expires in 3 days (storage.to) or 72 hours (litterbox).
Zip file: $ZipName
"@

try {
    $smtp = New-Object System.Net.Mail.SmtpClient("smtp.gmail.com", 587)
    $smtp.EnableSsl = $true
    $smtp.Credentials = New-Object System.Net.NetworkCredential($SmtpUser, $SmtpPassword)

    $mail = New-Object System.Net.Mail.MailMessage
    $mail.From = $SmtpUser
    foreach ($recipient in $recipientList) {
        $mail.To.Add($recipient)
    }
    $mail.Subject = "Download link: $ZipName"
    $mail.Body = $body

    $smtp.Send($mail)
    Write-Host "Email sent to: $($recipientList -join ', ')"
    exit 0
}
catch {
    Write-Warning "Email failed: $($_.Exception.Message)"
    exit 1
}

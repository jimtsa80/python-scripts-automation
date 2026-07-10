# Define parameters and paths

#today = (Get-Date).ToString("yyyyMMdd")
$sourceUrl = "https://isieve.blob.core.windows.net/tennis/2025 AO World Feed/*?sv=2022-11-02&ss=b&srt=sco&sp=rwdlaciytfx&se=2099-09-05T22:45:03Z&st=2024-05-16T14:45:03Z&spr=https&sig=yVBZ2bDqiv%2BcsRyvHXfH1SPlvNoUM0fzu3qCmiavjVc%3D"
$destinationPath = "D:\downloads\newbatch"
$pythonScriptPath = "C:\Users\jimtsa\Desktop\python-scripts-automation\imagesSimilarity\run_lite.ps1"
$logFile = "D:\downloads\task_log.txt"

# Log helper function
function Write-Log {
    param ([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "$timestamp - $message"
    Write-Output $entry | Out-File -Append -FilePath $logFile
}

# Step 1: Run AzCopy to download files
Write-Host "Running AzCopy..."
Write-Log "Starting AzCopy..."
try {
    $azCopyCommand = "azcopy copy '$sourceUrl' '$destinationPath' --include-pattern '*20250132_AO*' --recursive=True"
    Write-Host "Executing: $azCopyCommand"
    Write-Log "Executing AzCopy command: $azCopyCommand"
    Invoke-Expression $azCopyCommand
    Write-Log "AzCopy completed successfully."
} catch {
    Write-Log "AzCopy failed: $($_.Exception.Message)"
    Write-Host "AzCopy failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Add a small pause
Write-Host "Pausing for 15 seconds before executing Python script..."
Write-Log "Pausing for 15 seconds before executing Python script..."
Start-Sleep -Seconds 15

# Ensure the execution policy is set properly
Write-Host "Setting Execution Policy to Bypass for CurrentUser..."
Write-Log "Setting Execution Policy to Bypass for CurrentUser..."
try {
    powershell Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass -Force
    Write-Log "Execution Policy set to Bypass."
} catch {
    Write-Log "Failed to set Execution Policy: $($_.Exception.Message)"
    Write-Host "Failed to set Execution Policy: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 2: Execute the Python script
Write-Host "Running Python script..."
Write-Log "Starting Python script execution..."
try {
    # Set the working directory for Python scripts
    $workingDirectory = "C:\Users\jimtsa\Desktop\python-scripts-automation\imagesSimilarity"
    Set-Location -Path $workingDirectory
    Write-Host "Working directory set to $workingDirectory"
    Write-Log "Working directory set to $workingDirectory"
    
    # Constructing the script execution command
    $scriptExecutionCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$pythonScriptPath`" `"$destinationPath`" -mode simple -clusters 10 -threshold 0.99"
    Write-Host "Executing: $scriptExecutionCommand"
    Write-Log "Executing Python script command: $scriptExecutionCommand"
    
    # Execute the Python script
    Invoke-Expression $scriptExecutionCommand

    Write-Log "Python script executed successfully."
} catch {
    Write-Log "Python script failed: $($_.Exception.Message)"
    Write-Host "Python script failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# # Step 3 (Optional): Upload ZIP files to the remote server using SCP
# Write-Host "Uploading ZIP files..."
# Write-Log "Starting file upload..."
# try {
#     $zipFiles = Get-ChildItem -Path $destinationPath -Recurse -Include *.zip
#     foreach ($file in $zipFiles) {
#         $scpCommand = "sshpass -p '$password' scp `"$($file.FullName)`" `"$remoteServer`:$remotePath`""
#         Write-Host "Executing: $scpCommand"
#         Write-Log "Uploading file: $($file.FullName) using command: $scpCommand"
#         Invoke-Expression $scpCommand
#     }
#     Write-Log "File upload completed successfully."
# } catch {
#     Write-Log "File upload failed: $($_.Exception.Message)"
#     Write-Host "File upload failed: $($_.Exception.Message)" -ForegroundColor Red
# }

Write-Host "All tasks completed successfully."
Write-Log "All tasks completed successfully."

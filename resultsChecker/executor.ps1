param (
    [string]$sourceFolder,     # First argument: Source folder
    [string]$targetFolder      # Second argument: Target folder
)

# Define the Python script and its fixed third argument
$pythonScript = ".\importerResults.py"
$arg3 = "new"

# Log file location
$logFile = ".\executor.log"

# Start logging
Start-Transcript -Path $logFile -Append

# Check if source folder exists
if (!(Test-Path -Path $sourceFolder)) {
    Write-Output "Source folder does not exist."
    Stop-Transcript
    exit
}

# Ensure the target folder exists or create it
if (!(Test-Path -Path $targetFolder)) {
    New-Item -ItemType Directory -Path $targetFolder | Out-Null
}

# Copy each XLSX file from the source to the target and run the Python script
Get-ChildItem -Path $sourceFolder -Filter "*.xlsx" | ForEach-Object {
    $file = $_
    $destination = Join-Path -Path $targetFolder -ChildPath $file.Name
    Copy-Item -Path $file.FullName -Destination $destination
    Write-Output "Copied $($file.Name) to $targetFolder"

    # Execute the Python script with $targetFolder as both the first and second arguments
    Write-Output "Running Python script on $($file.Name)..."
    python $pythonScript $targetFolder $targetFolder $arg3
}

# Stop logging
Stop-Transcript

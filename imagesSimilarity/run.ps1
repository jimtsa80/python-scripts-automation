param (
    [string]$parent_dir = (Get-Location)
)

# Check if the provided parent directory exists
if (-Not (Test-Path $parent_dir)) {
    Write-Host "The specified directory does not exist: $parent_dir"
    exit
}

# Run the counterToGS.py and unzipper.py scripts with the $parent_dir as an argument
python counterToGS.py "$parent_dir"
python unzipper.py "$parent_dir"

# Delete all .zip files in the parent directory and print the name of each deleted file
Get-ChildItem -Path $parent_dir -Filter *.zip | ForEach-Object {
    Remove-Item $_.FullName
    Write-Host "Deleted zip file: $($_.Name)"
}

# Loop through each folder in the parent directory
Get-ChildItem -Path $parent_dir -Directory | ForEach-Object {
    $folder = $_.FullName
    $folder_name = $_.Name

    # Skip the folder named "toBeFinalized"
    if ($folder_name -eq "toBeFinalized") {
        Write-Host "Skipping folder: $folder_name"
        return
    }

    # Run the imagesComparison.py script with the folder as an argument
    python imagesComparison.py "$folder"

    # Wait for a few seconds to ensure the .xlsx file is created
    Start-Sleep -Seconds 5

    # Run the checker.py script with the folder and the Excel file as arguments
    python checker.py "$folder" "$folder_name.xlsx"
}

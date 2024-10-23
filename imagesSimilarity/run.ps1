#powershell -ExecutionPolicy Bypass -File .\run.ps1 .\batch2\ -mode simple -h5_type baseball

param (
    [string]$parent_dir = (Get-Location),
    [string]$mode = "simple", # Default mode is 'simple', can be set to 'strict'
    [string]$h5_type = "*"  # The * part of the H5 file
)

# Check if the provided parent directory exists
if (-Not (Test-Path $parent_dir)) {
    Write-Host "The specified directory does not exist: $parent_dir"
    exit
}

# Run the counterToGS.py and unzipper.py scripts with the $parent_dir as an argument
python counterToGS.py "$parent_dir"
python unzipper.py "$parent_dir"

# Delete all .zip and .7z files in the parent directory and print the name of each deleted file
Get-ChildItem -Path $parent_dir | Where-Object { $_.Extension -eq ".zip" -or $_.Extension -eq ".7z" } | ForEach-Object {
    Remove-Item $_.FullName
    Write-Host "Deleted file: $($_.Name)"
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

    # Run the appropriate imagesComparison script based on the mode argument
    if ($mode -eq "strict") {
        python imagesComparison_strict.py "$folder"
    } elseif ($mode -eq "simple") {
        python imagesComparison.py "$folder"
    } else {
        Write-Host "Invalid mode specified. Use 'strict' or 'simple'."
        exit
    }

    # Wait for a few seconds to ensure the .xlsx file is created
    Start-Sleep -Seconds 5

    # Run the checker.py script with the folder and the Excel file as arguments
    python checker.py "$folder" "$folder_name.xlsx"

    Start-Sleep -Seconds 5

    # Find the folder starting with "reduced"
    $reduced_folder = Get-ChildItem -Path $folder -Directory | Where-Object { $_.Name -like "reduced*" } | Select-Object -First 1

    if ($reduced_folder) {
        $reduced_folder_fullpath = $reduced_folder.FullName

        # Only run classifier if $h5_type is "baseball" or "cricket"
        if ($h5_type -eq "baseball" -or $h5_type -eq "cricket") {
            $h5_file = "C:\Users\jimtsa\Desktop\python-scripts-automation\imagesClassification\advertisement_${h5_type}_classifier.h5"
            python "C:\Users\jimtsa\Desktop\python-scripts-automation\imagesClassification\classifier.py" $h5_file "$reduced_folder_fullpath"
        } else {
            Write-Host "Skipping classifier execution for non-baseball/cricket folder: $folder_name"
        }
    } else {
        Write-Host "No 'reduced' folder found in: $folder_name"
    }
}

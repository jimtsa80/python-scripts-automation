param (
    [string]$parent_dir = (Get-Location),
    [string]$mode = "simple", # Default mode is 'simple', can be set to 'strict'
    [string]$keyword = "*",  # The * part of the H5 file
    [string]$clusters = "5",  # Default cluster count
    [string]$threshold = "0.99"  # Default threshold
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

# Check if any folders contain "smash" before running nzRenamer.py
$folders = Get-ChildItem -Path $parent_dir -Directory | Where-Object { $_.Name -match "smash" }

if ($folders) {
    python nzRenamer.py "$parent_dir"
} else {
    Write-Host "No folders containing 'smash' found. nzRenamer.py not executed."
}

# Check if any folder contains "WomenWC" and run delete_every_2nd_image.py inside those folders
$womenFolders = Get-ChildItem -Path $parent_dir -Directory -Recurse | Where-Object { $_.Name -match "URC" }

if ($womenFolders) {
    foreach ($folder in $womenFolders) {
        Write-Host "Found 'URC' folder: $($folder.FullName). Running delete_every_2nd_image.py..."
        python delete_every_2nd_image.py "$($folder.FullName)"
    }
} else {
    Write-Host "No folders containing 'WomenWC' found. Skipping delete_every_2nd_image.py."
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
    python checker.py "$folder" "$folder_name.xlsx" $threshold

    if ($clusters -ne "") {
        # Find the folder starting with "reduced"
        $reduced_folder = Get-ChildItem -Path $folder -Directory | Where-Object { $_.Name -like "reduced*" } | Select-Object -First 1

        if ($reduced_folder) {
            $reduced_folder_fullpath = $reduced_folder.FullName

            # Run classifier only if $keyword is "baseball" or "horse_racing"
            if ($keyword -eq "baseball" -or $keyword -eq "horse_racing") {
                $keywords_file = "C:\Users\jimtsa\Desktop\python-scripts-automation\imagesClassification\${keyword}_keywords.txt"
                python "C:\Users\jimtsa\Desktop\python-scripts-automation\imagesClassification\BLIPclassifier.py" "$reduced_folder_fullpath" $keywords_file 
            }
        } else {
            Write-Host "No 'reduced' folder found in: $folder"
        }
    } else {
        Write-Host "Skipping cluster creation due to empty clusters parameter."
    }
}

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

    Start-Sleep -Seconds 5

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

            python makeClusters.py $reduced_folder_fullpath $clusters

            #python sortImagesBySimilarity_folders.py $reduced_folder_fullpath

            # # # Run sortImagesBySimilarity.py for all clusters
            # Get-ChildItem -Path $reduced_folder_fullpath -Directory | Where-Object { $_.Name -match "cluster_*" } | ForEach-Object {
            #     Write-Host "Running sortImagesBySimilarity.py on $($_.Name)"
            #     python .\sortImagesBySimilarity.py "$($_.FullName)"
            # }

            # Run ocr_brands.py on all folders in $reduced_folder_fullpath
            # Find OCR_brands.txt in the same directory as ocr_brands.py (imagesSimilarity folder)
            $script_dir = Split-Path -Parent $MyInvocation.MyCommand.Path
            $brands_file = Join-Path $script_dir "OCR_brands2.txt"
            
            if (Test-Path $brands_file) {
                Write-Host "Running OCR brand detection on all folders in: $reduced_folder_fullpath"
                Write-Host "Using brands file: $brands_file"
                # Call ocr_brands.py once with the parent folder to process all subfolders into one output folder
                python ocr_brands.py "$reduced_folder_fullpath" "$brands_file" --gpu --workers 4 --fuzzy-threshold 0.7 --min-confidence 0.4
                
            } else {
                Write-Host "Warning: OCR_brands.txt not found in $reduced_folder_fullpath. Skipping OCR brand detection."
            }

            python zipFolders.py $reduced_folder_fullpath
            
            # Create a new folder inside the 'reduced_folder_fullpath' without the "reduced_" prefix
            $new_folder_name = $reduced_folder.Name -replace "^reduced_", ""
            $new_folder_path = Join-Path $reduced_folder_fullpath $new_folder_name

            if (-Not (Test-Path $new_folder_path)) {
                New-Item -ItemType Directory -Path $new_folder_path | Out-Null
                Write-Host "Created folder: $new_folder_path"
            }

            # Move all .zip files into the newly created folder
            Get-ChildItem -Path $reduced_folder_fullpath -Filter "*.zip" | ForEach-Object {
                $source = $_.FullName
                $destination = Join-Path -Path $new_folder_path -ChildPath $_.Name

                # Use the `\\?\` prefix to support long paths
                $source_long = "\\?\$source"
                $destination_long = "\\?\$destination"

                try {
                    Move-Item -Path $source_long -Destination $destination_long -ErrorAction Stop
                    Write-Host "Moved file: $($_.Name) to $new_folder_path"
                } catch {
                    Write-Host "Failed to move file: $($_.Name). Error: $_"
                }
            }
        } else {
            Write-Host "No 'reduced' folder found in: $folder"
        }
    } else {
        Write-Host "Skipping cluster creation due to empty clusters parameter."
    }
}

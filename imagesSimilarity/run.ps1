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

        # Run sortImagesBySimilarity.py for all clusters in the reduced folder
        Get-ChildItem -Path $reduced_folder_fullpath -Directory | Where-Object { $_.Name -match "cluster_*" } | ForEach-Object {
            Write-Host "Running sortImagesBySimilarity.py on $($_.FullName)"
            python ".\sortImagesBySimilarity.py" "$($_.FullName)"
        }

        # Second loop: Run imagesComparison.py for all folders in the reduced folder
        $allFolders = Get-ChildItem -Path $reduced_folder_fullpath -Directory
        $allFolders | ForEach-Object {
            Write-Host "Running imagesComparison.py on $($_.Name)"
            python ".\imagesComparison.py" "$($_.FullName)"
        }

        # Third loop: Run checkerPlus.py for all folders with incrementing cluster names
        $allFolders | ForEach-Object -Begin { $index = 0 } -Process {
            # Here, we correctly reference the .xlsx file in the root directory
            $clusterName = Join-Path -Path (Get-Location) -ChildPath "reduced_$folder_name-cluster_$index.xlsx"
            Write-Host "Running checkerPlus.py on $($_.Name) with output file $clusterName"
            
            # Ensure the .xlsx file exists before running the script
            if (Test-Path $clusterName) {
                python ".\checkerPlus.py" "$($_.FullName)" "$clusterName"
            } else {
                Write-Host "Warning: Excel file does not exist at: $clusterName"
            }
            
            $index++
        }

        # Iterate through all folders in $allFolders and move any .zip files to the parent $folder
        $allFolders | ForEach-Object {
            $currentFolder = $_.FullName
            Write-Host "Checking for .zip files in: $currentFolder"

            Get-ChildItem -Path $currentFolder -File | Where-Object { $_.Extension -eq ".zip" } | ForEach-Object {
                $zipFile = $_.FullName
                $destination = Join-Path -Path $folder -ChildPath $_.Name
                
                Write-Host "Moving $zipFile to $destination"
                Move-Item -Path $zipFile -Destination $destination
            }
        }

        # Rename all .zip files in $folder starting with "reduced_reduced"
        $counter = 1
        Get-ChildItem -Path $folder -File | Where-Object { $_.Extension -eq ".zip" -and $_.BaseName -like "reduced_reduced*" } | ForEach-Object {
        # Remove 'reduced_reduced_' from the file name
            $baseNameWithoutPrefix = $_.BaseName -replace '^reduced_', ''
            
            # Create the new name with a 'part_' prefix
            $newName = "part${counter}_$baseNameWithoutPrefix$($_.Extension)"
            $newPath = Join-Path -Path $folder -ChildPath $newName
            
            Write-Host "Renaming $($_.Name) to $newName"
            Rename-Item -Path $_.FullName -NewName $newPath
            
            $counter++
            }
        
        # python counter.py $folder

        } else {
            Write-Host "No 'reduced' folder found in: $folder"
        }
    } else {
        Write-Host "Skipping cluster creation due to empty clusters parameter."
    }
}

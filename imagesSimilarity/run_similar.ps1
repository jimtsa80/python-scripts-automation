#powershell -ExecutionPolicy Bypass -File .\run_similar.ps1 F:\downloads\batch6 -download -resize

param (
    [string]$parent_dir = (Get-Location),
    [Nullable[int]]$clusters, # Clustering happens only if this is defined
    [switch]$sorting,         # Sorting is off by default; enabled with -sorting
    [string]$sourceUrl = "https://isieve.blob.core.windows.net/wrc/*?sv=2022-11-02&ss=b&srt=sco&sp=rwdlaciytfx&se=2099-09-05T22:45:03Z&st=2024-05-16T14:45:03Z&spr=https&sig=yVBZ2bDqiv%2BcsRyvHXfH1SPlvNoUM0fzu3qCmiavjVc%3D",
    [string]$destinationPath = $parent_dir,
    [switch]$download,        # Download is off by default; enabled with -download
    [string]$fileListPath = "F:\downloads\filelist.txt",
    [switch]$trim,
    [string]$start,
    [string]$end,
    [switch]$resize          # New flag for resizing
)

# 1. Download if -download
if ($download) {
    Write-Host "Running AzCopy..."
    try {
        $azCopyCommand = "azcopy copy '$sourceUrl' '$destinationPath' --list-of-files '$fileListPath' --recursive=True"
        Write-Host "Executing: $azCopyCommand"
        Invoke-Expression $azCopyCommand
    } catch {
        Write-Host "AzCopy failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

if (-Not (Test-Path $parent_dir)) {
    Write-Host "The specified directory does not exist: $parent_dir"
    exit
}

# 2. Preprocessing
python counterToGS.py "$parent_dir"
python unzipper.py "$parent_dir"

# 3. Remove .zip/.7z files
Get-ChildItem -Path $parent_dir | Where-Object { $_.Extension -eq ".zip" -or $_.Extension -eq ".7z" } | ForEach-Object {
    Remove-Item $_.FullName
    Write-Host "Deleted file: $($_.Name)"
}

# 4. Splitting Large Folders
$folders_for_grouping = @()
Write-Host "Checking for folders with more than 20,000 files..."

Get-ChildItem -Path $parent_dir -Directory | ForEach-Object {
    $folder = $_
    $folder_path = $folder.FullName

    # Get only files directly in this directory, NOT subfolders
    $fileList = Get-ChildItem -Path $folder_path -File
    $fileCount = $fileList.Count

    if ($fileCount -gt 20000) {
        Write-Host "Splitting $folder_path ($fileCount files) into folders of max 10,000 files..."

        $baseName = $folder.Name
        $parentOfFolder = Split-Path $folder_path -Parent
        $allFiles = $fileList | Sort-Object Name # Sorted so split is deterministic
        $numberOfParts = [Math]::Ceiling($fileCount / 10000)

        for ($part=0; $part -lt $numberOfParts; $part++) {
            $startIdx = $part * 10000
            $endIdx = [Math]::Min($startIdx + 9999, $fileCount-1)
            $filesForThisPart = $allFiles[$startIdx..$endIdx]

            $newFolderName = "${baseName}_part$($part+1)"
            $newFolderPath = Join-Path $parentOfFolder $newFolderName
            if (-not (Test-Path $newFolderPath)) {
                New-Item -ItemType Directory -Path $newFolderPath | Out-Null
            }
            Write-Host " Moving files $($startIdx+1) to $($endIdx+1) into $newFolderName ($($filesForThisPart.Count) files)"
            foreach ($f in $filesForThisPart) {
                Move-Item -Path $f.FullName -Destination $newFolderPath
            }
            $folders_for_grouping += $newFolderPath
        }
        Write-Host "Removing original large folder: $folder_path"
        Remove-Item -Path $folder_path -Force -Recurse
    } else {
        Write-Host "Folder $folder_path has $fileCount files, no split needed."
        $folders_for_grouping += $folder_path
    }
}

Write-Host "`nSplit complete. Folders to process for grouping: $($folders_for_grouping.Count)"
foreach ($f in $folders_for_grouping) {
    Write-Host " Folder queued: $f"
}

# 5. MAIN LOOP - as usual, now using $folders_for_grouping!
foreach ($folder_to_process in $folders_for_grouping) {
    $folder_path = $folder_to_process
    Write-Host "`n---- Processing folder: $folder_path ----"

    if ($trim) {
        Write-Host " Trimming with folderTrimmer.py $folder_path $start $end"
        python folderTrimmer.py "$folder_path" $start $end
    }

    if ($resize) {
        Write-Host " Resizing images in: $folder_path"
        python resizer.py "$folder_path"
    }

    Write-Host " Running makeSimilarGroups.py $folder_path"
    python makeSimilarGroups.py "$folder_path"

    $reduced_folder_name = "reduced_" + (Split-Path $folder_path -Leaf)
    $reduced_folder_path = Join-Path $parent_dir $reduced_folder_name

    if (-Not (Test-Path $reduced_folder_path)) {
        New-Item -ItemType Directory -Path $reduced_folder_path | Out-Null
        Write-Host " Created folder: $reduced_folder_path"
    }

    if ($clusters -ne $null) {
        Write-Host " Creating clusters with $clusters clusters..."
        python makeClusters.py "$reduced_folder_path" $clusters
    } else {
        Write-Host " Skipping clustering as no cluster count was provided."
    }

    if ($sorting) {
        Get-ChildItem -Path $reduced_folder_path -Directory | Where-Object { $_.Name -match "cluster_*" } | ForEach-Object {
            Write-Host " Running sortImagesBySimilarity.py on $($_.FullName)"
            python ".\sortImagesBySimilarity.py" "$($_.FullName)"
        }
        Write-Host " Skipping zipping step since sorting is enabled."
    } else {
        python zipFolders.py "$reduced_folder_path"

        Get-ChildItem -Path $reduced_folder_path -Filter "*.zip" | ForEach-Object {
            $source = $_.FullName
            $destination = Join-Path $folder_path $_.Name
            try {
                Move-Item -Path $source -Destination $destination -ErrorAction Stop
                Write-Host " Moved file: $($_.Name) to $folder_path"
            } catch {
                Write-Host " Failed to move file: $($_.Name). Error: $_"
            }
        }

        Remove-Item -Path $reduced_folder_path -Recurse -Force
        Write-Host " Removed folder: $reduced_folder_path"
    }
}

Write-Host "`nAll folders have been processed!"
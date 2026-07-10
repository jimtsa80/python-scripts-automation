param (
    [string]$filePath,
    [string]$sequencesInfoPath,
    [switch]$social
)

#powershell -ExecutionPolicy Bypass -File

# Extract filename without the path and prepend 'final_'
$fileName = "final_" + [System.IO.Path]::GetFileName($filePath)

# Run Script 1: preprocess
Write-Output "Running Script 1..."
python preprocess.py $filePath
Write-Output "Duration to 1 everywhere"

# Run Script 2: Combines results with sequences_info
Write-Output "Running Script 2..." 
python combiner.py $sequencesInfoPath $fileName
Write-Output "Everything is combined"

# Run Script 3: Finalizer
Write-Output "Running Script 3..."
if ($social) {
    python aggregateXlsx.py .
    python finalizer_social.py $fileName
} else {
    python finalizer.py $fileName
}
Write-Output "Everything is finalized"


# ============================================================
#  Ftiaxnei ena ELAFRY zip me MONO ton kodika kai ta config,
#  xoris ta varia dedomena (eikones, video, audio, datasets,
#  model weights, caches, virtual environments).
#
#  Xrhsh:  .\make_code_zip.ps1
#  Apotelesma: ..\python-scripts-automation-code.zip
# ============================================================

$ErrorActionPreference = "Stop"

$root    = $PSScriptRoot
$zipPath = Join-Path (Split-Path $root -Parent) "python-scripts-automation-code.zip"

# Epektaseis pou KRATAME (kodikas + config + docs)
# Prosoxh: .json kai .txt DEN einai edo, giati edo einai kyrios
# dedomena (annotations, YOLO labels, filelists ~738MB). Ta
# simantika config json/txt ta kratame me to $keepNames pio kato.
$keepExt = @(
    ".py",".ps1",".bat",".cmd",".sh",".js",".ts",".jsx",".tsx",
    ".html",".htm",".css",".scss",".vue",
    ".md",".yaml",".yml",".toml",".cfg",".ini",
    ".sql",".r"
)

# Sygkekrimena onomata arxeion pou KRATAME panta (config/docs)
$keepNames = @(
    "requirements*.txt","README*","LICENSE*",".gitignore",
    "package.json","tsconfig*.json","hooks.json","*.config.json",
    "manifest.json","pyproject.toml","Dockerfile","Pipfile",".env.example"
)

# Fakeloi pou PARALEIPOUME teleios
$skipDirs = @(
    ".git","__pycache__","node_modules","tf_env","venv",".venv","env",
    "build","dist",".pytest_cache",".mypy_cache",".ipynb_checkpoints",
    ".idea",".vscode",".cursor"
)

# Megisto megethos arxeiou (akoma kai an einai kodikas/txt) -> apofygh giant data
$maxBytes = 3MB

Write-Host "==> Sarosh arxeion..." -ForegroundColor Cyan

$files = Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
    $rel = $_.FullName.Substring($root.Length).TrimStart('\')
    $parts = $rel.Split('\')
    # parelhpse an kapoios fakelos sto path einai sth lista
    $inSkip = $false
    foreach ($p in $parts) { if ($skipDirs -contains $p) { $inSkip = $true; break } }
    if ($inSkip) { return $false }
    if ($_.Length -gt $maxBytes) { return $false }
    # krata an einai gnosti epektash kodika
    if ($keepExt -contains $_.Extension.ToLower()) { return $true }
    # h an to onoma tairiazei me kapoio config pattern
    foreach ($pat in $keepNames) { if ($_.Name -like $pat) { return $true } }
    return $false
}

$count = ($files | Measure-Object).Count
$totalMB = [math]::Round((($files | Measure-Object -Property Length -Sum).Sum)/1MB, 1)
Write-Host "    Vrethikan $count arxeia ($totalMB MB)" -ForegroundColor DarkGray

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Write-Host "==> Dhmiourgia zip..." -ForegroundColor Cyan

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($zipPath, 'Create')
try {
    foreach ($f in $files) {
        $entryName = $f.FullName.Substring($root.Length).TrimStart('\').Replace('\','/')
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip, $f.FullName, $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
}
finally {
    $zip.Dispose()
}

$zipMB = [math]::Round((Get-Item $zipPath).Length/1MB, 2)
Write-Host ""
Write-Host "==> Etoimo: $zipPath  ($zipMB MB)" -ForegroundColor Green

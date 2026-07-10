# ============================================================
#  Setup script gia neo laptop
#  Egkathista ola ta Python packages me ta IDIA versions
#  opos sto palio mhxanhma (Python 3.11.0, global install).
#
#  Tropos xrhshs:
#    1. Egkatesthse Python 3.11.0 (deite README_MIGRATION.md)
#    2. Anoikse PowerShell se afton ton fakelo
#    3. Trekse:  .\setup_new_laptop.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "==> Elegxos ekdoshs Python..." -ForegroundColor Cyan
$pyVersion = (python --version) 2>&1
Write-Host "    $pyVersion"

if ($pyVersion -notmatch "3\.11") {
    Write-Host "PROSOXH: Den vrethike Python 3.11.x. Sunistatai Python 3.11.0 gia idia versions." -ForegroundColor Yellow
    $ans = Read-Host "Theleis na sunexiseis paroli ayto; (y/n)"
    if ($ans -ne "y") { exit 1 }
}

Write-Host "==> Anavathmish pip / setuptools / wheel..." -ForegroundColor Cyan
python -m pip install --upgrade pip setuptools wheel

Write-Host "==> Egkatastash packages apo to requirements.txt..." -ForegroundColor Cyan
Write-Host "    (Mporei na parei arketh wra - einai ~427 packages)" -ForegroundColor DarkGray
python -m pip install -r requirements.txt

Write-Host ""
Write-Host "==> Egine! Elegxos kritikon packages:" -ForegroundColor Green
python -c "import torch, tensorflow, cv2, numpy, pandas; print('torch', torch.__version__); print('tf', tensorflow.__version__); print('cv2', cv2.__version__); print('numpy', numpy.__version__)"

Write-Host ""
Write-Host "YPENTHYMISH: Ta audio scripts (pydub, librosa, faster-whisper) xreiazontai FFmpeg." -ForegroundColor Yellow
Write-Host "Egkatestise to me:  winget install Gyan.FFmpeg" -ForegroundColor Yellow

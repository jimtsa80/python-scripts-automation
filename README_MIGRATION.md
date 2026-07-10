# Μεταφορά Python setup σε νέο laptop

Αυτός ο οδηγός σε βοηθάει να στήσεις το **ίδιο ακριβώς** Python περιβάλλον
(ίδια versions) σε άλλο μηχάνημα Windows.

## Τι έχει το τωρινό setup

- **Python:** 3.11.0 (global install, στο `D:\Python3`)
- **Πακέτα:** ~427, καταγεγραμμένα με ακριβή version στο `requirements.txt`
- **PyTorch:** μετατράπηκε σε **CPU build** (αφαιρέθηκε το `+cu121`),
  γιατί το νέο laptop δεν έχει NVIDIA GPU.

## Βήματα στο νέο laptop

### 1. Εγκατάσταση Python 3.11.0

Κατέβασε τον installer για Windows από:
https://www.python.org/downloads/release/python-3110/
(αρχείο: *Windows installer (64-bit)*)

Στον installer:
- Τσέκαρε **"Add python.exe to PATH"**
- Κάνε εγκατάσταση

Επιβεβαίωσε σε νέο PowerShell:

```powershell
python --version   # πρέπει να δείξει Python 3.11.0
```

### 2. Αντιγραφή του project

Αντίγραψε όλο τον φάκελο `python-scripts-automation` στο νέο laptop
(USB, OneDrive, ή `git clone` αν είναι σε remote).
Σιγουρέψου ότι περιλαμβάνεται το `requirements.txt`.

### 3. Εγκατάσταση όλων των πακέτων

Άνοιξε PowerShell μέσα στον φάκελο και τρέξε:

```powershell
.\setup_new_laptop.ps1
```

Ή χειροκίνητα:

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

### 4. FFmpeg (για τα audio scripts)

Τα scripts στον φάκελο `audio/` (pydub, librosa, faster-whisper)
χρειάζονται το FFmpeg εγκατεστημένο στο σύστημα:

```powershell
winget install Gyan.FFmpeg
```

(ή κατέβασέ το από https://www.gyan.dev/ffmpeg/builds/ και βάλ' το στο PATH)

## Σημειώσεις

- Αν χρειαστείς ξανά τις GPU εκδόσεις του PyTorch (νέο laptop με NVIDIA),
  εγκατέστησέ τες ξεχωριστά:
  ```powershell
  pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
  ```
- Αν κάποιο πακέτο αποτύχει στην εγκατάσταση, το `requirements.txt` συνεχίζει
  μέχρι εκεί· τρέξε ξανά την εντολή ή εγκατέστησε το προβληματικό πακέτο μόνο του.

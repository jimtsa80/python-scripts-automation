import os
import zipfile
import sys
import shutil
from pathlib import Path

# python zipFolders.py "F:\downloads\batch17" --batch --ranges-file "C:\Users\jimtsa\Desktop\python-scripts-automation\imagesSimilarity\clean_ranges.txt"

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}

def safe_path(path):
    """Ensures Windows handles long file paths correctly by adding the \\?\ prefix if needed."""
    if sys.platform == "win32" and not path.startswith("\\\\?\\"):
        return f"\\\\?\\{path}"
    return path

def zip_folders(parent_folder):
    parent_folder = safe_path(parent_folder)
    
    # Get and sort subfolders
    subfolders = [f for f in os.listdir(parent_folder) if os.path.isdir(os.path.join(parent_folder, f))]
    subfolders.sort()

    for i, folder_name in enumerate(subfolders, start=1):
        old_folder_path = os.path.join(parent_folder, folder_name)
        
        # Check if folder already starts with "part"
        if folder_name.startswith("part"):
            # Skip renaming, use original folder name
            folder_to_zip = folder_name
            folder_path_to_zip = old_folder_path
            print(f"Skipping rename for {folder_name} (already starts with 'part')")
        else:
            # Rename the folder
            new_folder_name = f"part{i}_{folder_name}"
            new_folder_path = os.path.join(parent_folder, new_folder_name)

            # Apply safe path conversion
            old_folder_path = safe_path(old_folder_path)
            new_folder_path = safe_path(new_folder_path)

            # Rename the folder safely (skip if already renamed)
            if not os.path.exists(new_folder_path):
                os.rename(old_folder_path, new_folder_path)
                print(f"Renamed {folder_name} to {new_folder_name}")
            
            folder_to_zip = new_folder_name
            folder_path_to_zip = new_folder_path

        # Zip the folder
        folder_path_to_zip = safe_path(folder_path_to_zip)
        zip_file_path = os.path.join(parent_folder, f"{folder_to_zip}.zip")
        shutil.make_archive(zip_file_path.replace(".zip", ""), 'zip', folder_path_to_zip)
        print(f"Zipped {folder_to_zip} into {zip_file_path}")

def read_first_column(ranges_file):
    """Διαβάζει μόνο την πρώτη στήλη (ονόματα φακέλων) από το clean_ranges.txt."""
    names = []
    p = Path(ranges_file)
    with p.open("r", encoding="utf-8-sig") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            name = line.split(",")[0].strip()
            if name:
                names.append(name)
    return names


def find_reduced_folder(base, name):
    """Βρίσκει το base/<name>/reduced_<name> (αναδρομικά αν χρειαστεί)."""
    base = Path(base)
    matched = base / name
    if not matched.is_dir():
        return None
    target = f"reduced_{name}"
    direct = matched / target
    if direct.is_dir():
        return direct
    for foldername, subfolders, _files in os.walk(matched):
        for sub in subfolders:
            if sub == target:
                return Path(foldername) / sub
    return None


def count_images_in_zip(zip_path):
    count = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            ext = os.path.splitext(info.filename)[1].lower()
            if ext in _IMAGE_EXTS:
                count += 1
    return count


def run_batch(batch_folder, ranges_file):
    if not os.path.isdir(batch_folder):
        print(f"The provided path {batch_folder} is not a valid directory.")
        return 1
    if not os.path.isfile(ranges_file):
        print(f"Ranges file not found: {ranges_file}")
        return 1

    names = read_first_column(ranges_file)
    print(f"Read {len(names)} folder names from: {ranges_file}")
    print(f"Batch path: {batch_folder}")

    processed = 0
    problems = []
    for name in names:
        reduced = find_reduced_folder(batch_folder, name)
        if reduced is None:
            problems.append(f"Could not find reduced_ folder for: {name}")
            continue

        print(f"\nProcessing: {name}")

        # Zip the folders inside the reduced folder (existing behavior)
        zip_folders(str(reduced))

        # Create destination folder named like the txt entry
        dest = os.path.join(str(reduced), name)
        os.makedirs(safe_path(dest), exist_ok=True)

        # Move all zips into the new folder and count images inside them
        total_images = 0
        reduced_safe = safe_path(str(reduced))
        for entry in os.listdir(reduced_safe):
            if not entry.lower().endswith(".zip"):
                continue
            src_zip = os.path.join(str(reduced), entry)
            try:
                total_images += count_images_in_zip(safe_path(src_zip))
            except Exception as exc:
                problems.append(f"{name}: could not read {entry} ({exc})")
            dst_zip = os.path.join(dest, entry)
            shutil.move(safe_path(src_zip), safe_path(dst_zip))

        print(f"  {name}: total images inside zips = {total_images}")
        processed += 1

    print(f"\nProcessed {processed}/{len(names)} folders.")
    if processed != len(names):
        print("WARNING: not all folders were processed.")
    if problems:
        print(f"\nProblems ({len(problems)}):")
        for prob in problems:
            print(f"  - {prob}")
    return 0


def main():
    args = sys.argv[1:]

    # Batch mode: python zipFolders.py <batch_folder> --batch [--ranges-file FILE]
    if "--batch" in args:
        args = [a for a in args if a != "--batch"]
        ranges_file = str(Path(__file__).with_name("clean_ranges.txt"))
        if "--ranges-file" in args:
            idx = args.index("--ranges-file")
            ranges_file = args[idx + 1]
            del args[idx:idx + 2]
        if len(args) != 1:
            print("Usage: python zipFolders.py <batch_folder> --batch [--ranges-file FILE]")
            sys.exit(1)
        sys.exit(run_batch(args[0], ranges_file))

    # Old mode (unchanged)
    if len(args) != 1:
        print("Usage: python script.py <parent_folder>")
        sys.exit(1)

    parent_folder = args[0]

    if not os.path.isdir(parent_folder):
        print(f"The provided path {parent_folder} is not a valid directory.")
        sys.exit(1)

    zip_folders(parent_folder)

if __name__ == "__main__":
    main()

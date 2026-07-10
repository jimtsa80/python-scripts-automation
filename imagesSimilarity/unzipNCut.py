import os
import zipfile
import re
import argparse
from collections import defaultdict

def extract_zip_files(folder):
    extracted_folders = []
    has_zip = False
    for file in os.listdir(folder):
        if file.endswith(".zip"):
            has_zip = True
            zip_path = os.path.join(folder, file)
            extract_path = os.path.join(folder, os.path.splitext(file)[0])
            print(f"Extracting {file} to {extract_path}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            extracted_folders.append(extract_path)
    return extracted_folders, has_zip

def parse_txt_file(txt_file):
    """Parse text file and return a dictionary mapping keys to multiple ranges."""
    ranges = defaultdict(list)
    print(f"\nReading limits from {txt_file}")
    with open(txt_file, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                key = parts[0]
                start = int(parts[1].replace(',', ''))
                end = int(parts[2].replace(',', ''))
                ranges[key].append((start, end))
                print(f"  Parsed range for '{key}': {start}-{end}")
    return ranges

def filter_images(folder, ranges):
    print(f"\nFiltering images in {folder}")
    kept_nums = []
    kept_files = []
    deleted_count = 0
    processed_files = []

    for file in os.listdir(folder):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            match = re.search(r'\d+', file)
            full_path = os.path.join(folder, file)
            if match:
                num = int(match.group().lstrip('0') or '0')
                processed_files.append(file)
                if any(start <= num <= end for start, end in ranges):
                    print(f"Kept:     {file}")
                    kept_nums.append(num)
                    kept_files.append(file)
                else:
                    print(f"Deleted:  {file}")
                    os.remove(full_path)
                    deleted_count += 1
            else:
                print(f"Skipped (no number in filename): {file}")

    print("\nSummary for folder:")
    print(f"  Processed files: {len(processed_files)}")
    print(f"  Kept files: {len(kept_files)}")
    print(f"  Deleted files: {deleted_count}")

    if kept_nums:
        print(f"  Range of numbers kept: {min(kept_nums)} - {max(kept_nums)}")
    else:
        print("  No files kept in this folder (check your range and filenames).\n")

def get_subfolders(folder):
    return [
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if os.path.isdir(os.path.join(folder, name))
    ]

def main(folder):
    extracted_folders, has_zip = extract_zip_files(folder)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    txt_file = os.path.join(script_dir, "filesNlimits.txt")

    if not os.path.exists(txt_file):
        print("filesNlimits.txt not found.")
        return

    ranges_dict = parse_txt_file(txt_file)

    if has_zip:
        folders_to_process = extracted_folders
    else:
        # Check if input folder itself contains images (no subfolders)
        image_found = any(
            f.lower().endswith(('.jpg', '.jpeg', '.png')) for f in os.listdir(folder)
        )
        if image_found:
            folders_to_process = [folder]
        else:
            folders_to_process = get_subfolders(folder)

    print("\n--- RANGE KEYS FROM TXT FILE ---")
    for key, ranges in ranges_dict.items():
        print(f"  Key: '{key}', ranges: {ranges}")

    print("\n--- FOLDERS TO PROCESS ---")
    for f in folders_to_process:
        print(f"  Folder: '{f}'")

    for current_folder in folders_to_process:
        folder_name = os.path.basename(current_folder)
        found = False
        for key in ranges_dict:
            print(f"Checking if key '{key}' is in folder name '{folder_name}'")
            if key in folder_name:
                found = True
                print(f"\nProcessing folder: {current_folder} (matched key: '{key}')")
                print(f"Numbers to keep: {ranges_dict[key]}")
                filter_images(current_folder, ranges_dict[key])
                break
        if not found:
            print(f"No range key matched for folder '{folder_name}'\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unzip files and filter images based on range.")
    parser.add_argument("folder", help="Folder containing zip files or extracted folders or images")
    args = parser.parse_args()
    main(args.folder)
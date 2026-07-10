import os
import sys
import shutil

from pathlib import Path

def move_zips_to_target_root(target_folder):
    target_folder = Path(target_folder).resolve()
    target_root = target_folder.parent  # Move zips to parent of target_folder

    for root, dirs, files in os.walk(target_folder):
        for file in files:
            if file.lower().endswith('.zip'):
                file_path = Path(root) / file
                destination = target_root / file

                print(f"Moving {file_path} -> {destination}")
                shutil.move(str(file_path), str(destination))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python move_zips.py <target_folder>")
        sys.exit(1)

    target_folder = sys.argv[1]
    if not os.path.isdir(target_folder):
        print(f"Error: {target_folder} is not a valid folder")
        sys.exit(1)

    move_zips_to_target_root(target_folder)
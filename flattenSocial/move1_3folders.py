import os
import shutil
import random
import sys

def move_folders(parent_dir):
    # Strings to match
    target_strings = ["adelaideinternational", "unitedcuptennis", "brisbaneinternational"]

    # Verify if the parent directory exists
    if not os.path.isdir(parent_dir):
        print(f"The directory '{parent_dir}' does not exist.")
        return

    # List all folders in the parent directory
    all_folders = [folder for folder in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, folder))]

    # Create 'temp' directory at the same level as the parent directory
    temp_dir = os.path.join(parent_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Step 1: Move folders containing target strings
    matching_folders = [folder for folder in all_folders if any(target in folder for target in target_strings)]
    for folder in matching_folders:
        src = os.path.join(parent_dir, folder)
        dest = os.path.join(temp_dir, folder)
        shutil.move(src, dest)
        print(f"Moved: {src} -> {dest}")

    # Remove moved folders from the list
    remaining_folders = [folder for folder in all_folders if folder not in matching_folders]

    # Step 2: Randomly select and move 1/3 of the remaining folders
    num_to_move = len(remaining_folders) // 3
    if num_to_move > 0:
        folders_to_move = random.sample(remaining_folders, num_to_move)
        for folder in folders_to_move:
            src = os.path.join(parent_dir, folder)
            dest = os.path.join(temp_dir, folder)
            shutil.move(src, dest)
            print(f"Moved: {src} -> {dest}")

    print(f"Moved {len(matching_folders)} matching folders and {num_to_move} random folders to '{temp_dir}'.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python move_folders.py <parent_directory>")
    else:
        move_folders(sys.argv[1])
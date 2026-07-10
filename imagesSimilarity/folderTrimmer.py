import os
import sys
import glob
import shutil

def move_images(folder_path, ranges_file):
    # Define new folder name
    new_folder = f"{folder_path}_new"
    os.makedirs(new_folder, exist_ok=True)

    # Get all image files in the folder
    image_extensions = ("*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.tiff")
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder_path, ext)))

    # Sort files alphabetically
    image_files.sort()

    # Extract filenames without extensions (only numeric parts)
    base_names = [os.path.splitext(os.path.basename(f))[0] for f in image_files]

    # Read ranges from file
    move_files = set()
    try:
        with open(ranges_file, "r") as f:
            for line in f:
                parts = line.strip().split(",")  # Use comma as delimiter
                if len(parts) != 2:
                    print(f"Skipping invalid line: {line.strip()}")
                    continue

                start, end = int(parts[0]), int(parts[1])  # Read numeric range

                # Find matching files in the range
                for name, file in zip(base_names, image_files):
                    if name.isdigit():  # Ensure filename is purely numeric
                        number = int(name)  # Convert to integer for comparison
                        if start <= number <= end:
                            move_files.add(file)

    except FileNotFoundError:
        print(f"Error: File '{ranges_file}' not found.")
        sys.exit(1)

    # Move selected files
    for file in move_files:
        shutil.move(file, os.path.join(new_folder, os.path.basename(file)))

    print(f"Moved {len(move_files)} files to '{new_folder}'.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <folder_path> <ranges_file>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    ranges_file = sys.argv[2]
    
    move_images(folder_path, ranges_file)
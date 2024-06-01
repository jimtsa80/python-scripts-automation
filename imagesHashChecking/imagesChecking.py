import os
import hashlib
import sys
from openpyxl import Workbook

def compute_hash(file_path, algorithm='md5'):
    hash_algo = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_algo.update(chunk)
    return hash_algo.hexdigest()

def hash_images_in_folder(folder_path, output_file, algorithm='md5'):
    # Create a new workbook and select the active worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Image Hashes"
    
    # Write the header row
    ws.append(["Image Name", "Hash"])
    
    # Iterate over all files in the specified folder
    for root, dirs, files in os.walk(folder_path):
        print(f"Scanning directory: {root}")
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
                file_path = os.path.join(root, file)
                print(f"Processing file: {file_path}")
                file_hash = compute_hash(file_path, algorithm)
                print(f"Computed hash: {file_hash}")
                ws.append([file, file_hash])
    
    # Save the workbook to the specified file
    wb.save(output_file)
    print(f"Hashes written to {output_file}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <folder_path> <output_file>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    output_file = sys.argv[2]

    print(f"Folder path: {folder_path}")
    print(f"Output file: {output_file}")

    hash_images_in_folder(folder_path, output_file)

if __name__ == "__main__":
    main()

import os
import sys
import zipfile
import py7zr
import math
import shutil

def copy_images_to_folder(images_folder, source_folder):
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)
    for file_name in os.listdir(source_folder):
        if file_name.endswith('.jpeg'):
            shutil.copy(os.path.join(source_folder, file_name), images_folder)

def calculate_parts(images_folder, num_parts):
    num_files = len([f for f in os.listdir(images_folder) if f.endswith('.jpeg')])
    if num_parts > 10:
        num_parts = math.ceil(num_files / num_parts)
    return num_parts

def generate_ranges(num_files, num_parts):
    ranges = []
    start = 0
    for i in range(num_parts):
        end = min(start + num_files // num_parts, num_files)
        ranges.append((start, end))
        start = end + 1
    return ranges

def create_zip_archive(source_dir, destination_file):
    with zipfile.ZipFile(destination_file, 'w') as zip_ref:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zip_ref.write(file_path, arcname=arcname)

def main(input_file, num_parts=None, num_images_per_part=None):
    output_dir = os.path.dirname(os.path.abspath(input_file))

    images_folder = os.path.join(output_dir, "images")
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)

    if input_file.endswith('.zip'):
        with zipfile.ZipFile(input_file, 'r') as zip_ref:
            zip_ref.extractall(images_folder)
    elif input_file.endswith('.7z'):
        with py7zr.SevenZipFile(input_file, mode='r') as archive:
            archive.extractall(path=images_folder)
    else:
        print("Unsupported file format. Please provide a zip or 7z file.")
        return

    num_files = len([f for f in os.listdir(images_folder) if f.endswith('.jpeg')])

    if num_parts is None and num_images_per_part is None:
        print(f"Now the initial file has {num_files} images.")
        print("Please provide either the number of parts or the number of images per part.")
        return
    elif num_parts is None:
        num_parts = calculate_parts(images_folder, num_images_per_part)

    print(f"Now the initial file has {num_files} images.")
    print(f"{num_parts} parts will be created.")

    ranges = generate_ranges(num_files, num_parts)

    for idx, (start, end) in enumerate(ranges):
        part_dir = os.path.join(output_dir, f"part{idx+1}")
        if not os.path.exists(part_dir):
            os.makedirs(part_dir)

        for i in range(start, end):
            shutil.copy(os.path.join(images_folder, f'image_{i}.jpeg'), part_dir)

        part_zip_file = os.path.join(output_dir, f"part{idx+1}_{os.path.basename(input_file)}")
        create_zip_archive(part_dir, part_zip_file)

        print(f"Part {idx+1} created. It contains {end-start} images.")

    print("The partitions are:")
    for idx, (start, end) in enumerate(ranges):
        print(f"{start} \t {end}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <path_to_zip_or_7z_file> [num_parts_or_num_images_per_part]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    num_parts = None
    num_images_per_part = None

    if len(sys.argv) > 2:
        num_parts_or_images = sys.argv[2]
        try:
            num_parts = int(num_parts_or_images)
        except ValueError:
            num_images_per_part = int(num_parts_or_images)

    main(input_file, num_parts, num_images_per_part)

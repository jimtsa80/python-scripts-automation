import os
import zipfile
import tempfile
import shutil
import argparse
import struct
import re  # Import re module

# Monkey-patch zipfile._EndRecData64
def _EndRecData64(fpin, offset, endrec):
    """
    Read the ZIP64 end-of-archive records and use that to update endrec
    """
    try:
        fpin.seek(offset - zipfile.sizeEndCentDir64Locator, 2)
    except OSError:
        return endrec

    data = fpin.read(zipfile.sizeEndCentDir64Locator)
    if len(data) != zipfile.sizeEndCentDir64Locator:
        return endrec
    sig, diskno, reloff, disks = struct.unpack(
        zipfile.structEndArchive64Locator, data)
    if sig != zipfile.stringEndArchive64Locator:
        return endrec

    if diskno != 0 or disks > 1:
        raise zipfile.BadZipfile(
            "zipfiles that span multiple disks are not supported")

    fpin.seek(
        offset - zipfile.sizeEndCentDir64Locator - zipfile.sizeEndCentDir64, 2)
    data = fpin.read(zipfile.sizeEndCentDir64)
    if len(data) != zipfile.sizeEndCentDir64:
        return endrec
    sig, sz, create_version, read_version, disk_num, disk_dir, \
        dircount, dircount2, dirsize, diroffset = \
        struct.unpack(zipfile.structEndArchive64, data)
    if sig != zipfile.stringEndArchive64:
        return endrec

    endrec[zipfile._ECD_SIGNATURE] = sig
    endrec[zipfile._ECD_DISK_NUMBER] = disk_num
    endrec[zipfile._ECD_DISK_START] = disk_dir
    endrec[zipfile._ECD_ENTRIES_THIS_DISK] = dircount
    endrec[zipfile._ECD_ENTRIES_TOTAL] = dircount2
    endrec[zipfile._ECD_SIZE] = dirsize
    endrec[zipfile._ECD_OFFSET] = diroffset
    return endrec

zipfile._EndRecData64 = _EndRecData64

class TemporaryDirectory(object):
    def __enter__(self):
        self.name = tempfile.mkdtemp()
        return self.name

    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self.name)

# Define natural_sort_key function
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def print_jpeg_info(zip_path):
    num_images = 0
    first_jpeg = None
    last_jpeg = None

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        namelist = zip_ref.namelist()

        for filename in namelist:
            if filename.lower().endswith((".jpg", ".jpeg")):
                num_images += 1
                if not first_jpeg:
                    first_jpeg = filename
                last_jpeg = filename

    if num_images > 0:
        print("Total JPEGs in %s: %d" % (zip_path, num_images))
        print("First JPEG: %s" % first_jpeg)
        print("Last JPEG: %s" % last_jpeg)
    else:
        print("No JPEGs found in %s" % zip_path)

def split_zip(input_zip, num_parts):
    base_name = os.path.splitext(os.path.basename(input_zip))[0]

    try:
        with zipfile.ZipFile(input_zip, 'r') as zip_ref:
            with TemporaryDirectory() as temp_dir:
                print("Extracting files to temporary directory...")
                zip_ref.extractall(temp_dir)

                file_paths = []
                print("Collecting and sorting file paths...")
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_paths.append(os.path.join(root, file))

                # Use natural_sort_key for sorting file paths
                file_paths.sort(key=natural_sort_key)
                total_files = len(file_paths)
                print("Total number of files in zip: %s" % total_files)

                if num_parts > 15:
                    print("User gave %s parts, recalculating based on total number of files..." % num_parts)
                    num_parts = max(1, round(total_files / num_parts))
                    print("Adjusted number of parts: %s" % num_parts)
                
                files_per_part = total_files // num_parts
                remaining_files = total_files % num_parts

                part_num = 1
                files_in_current_part = 0
                current_zip_path = 'part%d_%s.zip' % (part_num, base_name)
                current_zip = zipfile.ZipFile(current_zip_path, 'w')

                for file_path in file_paths:
                    if files_in_current_part >= files_per_part + (1 if remaining_files > 0 else 0):
                        current_zip.close()
                        print_jpeg_info(current_zip_path)
                        part_num += 1
                        if remaining_files > 0:
                            remaining_files -= 1
                        files_in_current_part = 0
                        current_zip_path = 'part%d_%s.zip' % (part_num, base_name)
                        current_zip = zipfile.ZipFile(current_zip_path, 'w')

                    current_zip.write(file_path, os.path.relpath(file_path, temp_dir))
                    files_in_current_part += 1

                if files_in_current_part > 0:
                    current_zip.close()
                    print_jpeg_info(current_zip_path)
    except zipfile.BadZipfile as e:
        print("Error: %s" % str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split a ZIP file into multiple parts.")
    parser.add_argument('input_zip', help="Path to the input ZIP file.")
    parser.add_argument('num_parts', type=int, help="Number of parts to split the ZIP file into.")

    args = parser.parse_args()
    split_zip(args.input_zip, args.num_parts)

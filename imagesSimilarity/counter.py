import zipfile
import os
import sys
import struct
import subprocess
from pprint import pprint

# Monkey-patch zipfile._EndRecData64
def _EndRecData64(fpin, offset, endrec):
    """Read the ZIP64 end-of-archive records and use that to update endrec."""
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

def count_jpeg_in_zip(zip_file_path):
    jpeg_count = 0
    folder_jpeg_count = {}
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            for filename in zip_ref.namelist():
                if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    jpeg_count += 1
                    folder = os.path.dirname(filename)
                    if folder not in folder_jpeg_count:
                        folder_jpeg_count[folder] = 0
                    folder_jpeg_count[folder] += 1
            if not folder_jpeg_count:
                for info in zip_ref.infolist():
                    if info.filename.lower().endswith('.jpg') or info.filename.lower().endswith('.jpeg'):
                        jpeg_count += 1
                        folder_jpeg_count['.'] = folder_jpeg_count.get('.', 0) + 1
    except zipfile.BadZipfile:
        print("Error: {} is not a valid ZIP file.".format(zip_file_path))
    return jpeg_count, folder_jpeg_count

def count_jpeg_in_7z(archive_path):
    jpeg_count = 0
    folder_jpeg_count = {}
    print("Found 7z archive: {}".format(archive_path))
    try:
        # Use the 7z command-line tool to list the files in the archive
        output = subprocess.check_output(['7z', 'l', archive_path])
        print("Counting JPEG files in 7z archive...")
        for line in output.splitlines():
            parts = line.split()
            if len(parts) > 0:
                filename = parts[-1]
                if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    jpeg_count += 1
                    folder = os.path.dirname(filename) or '.'
                    if folder not in folder_jpeg_count:
                        folder_jpeg_count[folder] = 0
                    folder_jpeg_count[folder] += 1
    except subprocess.CalledProcessError:
        print("Error: {} is not a valid 7z file.".format(archive_path))
    except Exception as e:
        print("An error occurred: {}".format(e))
    return jpeg_count, folder_jpeg_count

def count_jpeg_in_folder(folder_path):
    total_jpeg_count = 0
    folder_jpeg_count = {}
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith('.zip'):
                zip_file_path = os.path.join(root, filename)
                count, nested_folder_jpeg_count = count_jpeg_in_zip(zip_file_path)
                
                total_jpeg_count += count
                folder_jpeg_count[filename] = count
                for folder, count in nested_folder_jpeg_count.items():
                    full_folder_path = os.path.join(os.path.relpath(root, folder_path), folder)
                    if full_folder_path not in folder_jpeg_count:
                        folder_jpeg_count[full_folder_path] = 0
                    folder_jpeg_count[full_folder_path] += count
            elif filename.lower().endswith('.7z'):
                archive_path = os.path.join(root, filename)
                count, nested_folder_jpeg_count = count_jpeg_in_7z(archive_path)
                
                total_jpeg_count += count
                folder_jpeg_count[filename] = count
                for folder, count in nested_folder_jpeg_count.items():
                    full_folder_path = os.path.join(os.path.relpath(root, folder_path), folder)
                    if full_folder_path not in folder_jpeg_count:
                        folder_jpeg_count[full_folder_path] = 0
                    folder_jpeg_count[full_folder_path] += count
    return total_jpeg_count, folder_jpeg_count

def process_input_path(input_path):
    total_jpeg_count = 0
    folder_jpeg_count = {}

    if os.path.isdir(input_path):
        total_jpeg_count, folder_jpeg_count = count_jpeg_in_folder(input_path)
        print("Summary of JPEG Files in Directory\n")
        print("Directory: '{}'\nTotal JPEG files: {}\n".format(input_path, total_jpeg_count))
        if folder_jpeg_count:
            print("Details by Subfolder:")
            pprint(folder_jpeg_count)
    elif input_path.lower().endswith('.zip'):
        total_jpeg_count, folder_jpeg_count = count_jpeg_in_zip(input_path)
        print("Summary of JPEG Files in ZIP Archive\n")
        print("ZIP Archive: '{}'\nTotal JPEG files: {}\n".format(input_path, total_jpeg_count))
        if folder_jpeg_count:
            print("Details by Subfolder:")
            pprint(folder_jpeg_count)
    elif input_path.lower().endswith('.7z'):
        total_jpeg_count, folder_jpeg_count = count_jpeg_in_7z(input_path)
        print("Summary of JPEG Files in 7z Archive\n")
        print("7z Archive: '{}'\nTotal JPEG files: {}\n".format(input_path, total_jpeg_count))
        if folder_jpeg_count:
            print("Details by Subfolder:")
            pprint(folder_jpeg_count)

    total_hours = total_jpeg_count / 3600.0

    print("Total number of JPEG files in all ZIP and 7z files: {}".format(total_jpeg_count))
    print("Total time in hours: {:.2f}".format(total_hours))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_or_zip_path>")
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print("Path not found!")
        sys.exit(1)

    process_input_path(input_path)

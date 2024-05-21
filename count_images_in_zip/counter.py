import zipfile
import os
import sys
import struct

# Monkey-patch zipfile._EndRecData64
def _EndRecData64(fpin, offset, endrec):
    """
    Read the ZIP64 end-of-archive records and use that to update endrec
    """
    try:
        fpin.seek(offset - zipfile.sizeEndCentDir64Locator, 2)
    except OSError:
        # If the seek fails, the file is not large enough to contain a ZIP64
        # end-of-archive record, so just return the end record we were given.
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

    # Assume no 'zip64 extensible data'
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

    # Update the original endrec using data from the ZIP64 record
    endrec[zipfile._ECD_SIGNATURE] = sig
    endrec[zipfile._ECD_DISK_NUMBER] = disk_num
    endrec[zipfile._ECD_DISK_START] = disk_dir
    endrec[zipfile._ECD_ENTRIES_THIS_DISK] = dircount
    endrec[zipfile._ECD_ENTRIES_TOTAL] = dircount2
    endrec[zipfile._ECD_SIZE] = dirsize
    endrec[zipfile._ECD_OFFSET] = diroffset
    return endrec

# Overwrite _EndRecData64 with the fixed version
zipfile._EndRecData64 = _EndRecData64

def count_jpeg_in_zip(zip_file_path):
    jpeg_count = 0
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            for filename in zip_ref.namelist():
                if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    jpeg_count += 1
    except zipfile.BadZipfile:
        print("Error: {} is not a valid ZIP file.".format(zip_file_path))
    return jpeg_count

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    if not os.path.exists(folder_path):
        print("Folder not found!")
    else:
        total_jpeg_count = 0
        for filename in os.listdir(folder_path):
            if filename.lower().endswith('.zip'):
                zip_file_path = os.path.join(folder_path, filename)
                count = count_jpeg_in_zip(zip_file_path)
                print("{} ==> {}".format(filename, count))
                total_jpeg_count += count
        
        # Calculate the total hours
        total_hours = total_jpeg_count / 3600.0
        
        print("Total number of JPEG files in all ZIP files: {}".format(total_jpeg_count))
        print("Total time in hours: {:.2f}".format(total_hours))







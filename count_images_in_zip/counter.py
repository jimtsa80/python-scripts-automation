import zipfile
import os
import sys

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




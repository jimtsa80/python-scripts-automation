import argparse
import zipfile
import os
import tempfile
import re


def split_zip(input_zip, num_parts, output_prefix="part"):
    """
    Splits a zip file containing JPEG images into smaller zip files.

    Args:
        input_zip (str): Path to the input zip file.
        num_parts (int): Number of smaller zip files to create.
        output_prefix (str, optional): Prefix for the output zip filenames. Defaults to "part".
    """

    with zipfile.ZipFile(input_zip, 'r') as in_zip:
        total_files = len(in_zip.namelist())
        print(f"Total files in {input_zip}: {total_files}")

        # Sort filenames by extracting numbering using regex
        namelist = sorted(in_zip.namelist(), key=lambda x: int(re.findall(r'\d+', x)[0]))

        if num_parts > 10:
            num_parts = round(total_files / num_parts)

        files_per_part = total_files // num_parts
        remainder = total_files % num_parts

        with tempfile.TemporaryDirectory() as temp_dir:
            for part_num in range(1, num_parts + 1):
                base_filename, _ = os.path.splitext(os.path.basename(input_zip))
                output_zip = os.path.join(temp_dir, f"{output_prefix}_{part_num}_{base_filename}.zip")

                with zipfile.ZipFile(output_zip, 'w') as out_zip:
                    start_index = (part_num - 1) * files_per_part
                    end_index = start_index + files_per_part
                    if part_num == num_parts:
                        end_index += remainder

                    for i in range(start_index, end_index):
                        info = in_zip.getinfo(namelist[i])
                        if info.filename.lower().endswith((".jpg", ".jpeg")):
                            with in_zip.open(info.filename) as file:
                                out_zip.writestr(os.path.basename(info.filename), file.read())
                        elif not has_folders(in_zip, info.filename):  # Not a folder or JPEG
                            print(f"Found non-JPEG file: {info.filename}. Skipping for this script.")
                        else:  # It's a folder, extract files within
                            for nested_file in in_zip.namelist():
                                if nested_file.startswith(info.filename) and not has_folders(in_zip, nested_file):
                                    with in_zip.open(nested_file) as nested_file_obj:
                                        # Extract the file with a relative path within the zip (remove folder structure)
                                        new_filename = os.path.relpath(nested_file, info.filename)
                                        out_zip.writestr(new_filename, nested_file_obj.read())

                final_output_zip = os.path.join(os.path.dirname(input_zip), f"part_{part_num}_{base_filename}.zip")
                os.replace(output_zip, final_output_zip)

                print_first_and_last_jpeg(final_output_zip)


def has_folders(zip_file, filename):
    """
    Checks if a file within a zip archive is a folder.

    Args:
        zip_file (zipfile.ZipFile): The opened zip file object.
        filename (str): The filename to check within the zip.

    Returns:
        bool: True if the filename points to a folder, False otherwise.
    """
    info = zip_file.getinfo(filename)
    return info.file_size == 0 or "/" in filename


def print_first_and_last_jpeg(zip_file):
    """
    Prints the first and last JPEG filenames, along with the total number of JPEGs, from a zip file.

    Args:
        zip_file (str): Path to the zip file.
    """

    num_images = 0
    first_jpeg = None
    last_jpeg = None

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        namelist = zip_ref.namelist()

        for filename in namelist:
            if filename.lower().endswith((".jpg", ".jpeg")):
                num_images += 1
                if not first_jpeg:
                    first_jpeg = filename
                last_jpeg = filename

    if num_images > 0:
        print(f"Total JPEGs in {zip_file}: {num_images}")
        print(f"First JPEG: {first_jpeg}")
        print(f"Last JPEG: {last_jpeg}")
    else:
        print(f"No JPEGs found in {zip_file}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split a zip file containing JPEG images.")
    parser.add_argument("input_zip", help="Path to the input zip file.")
    parser.add_argument("num_parts", type=int, help="Number of smaller zip files to create.")
    args = parser.parse_args()

    split_zip(args.input_zip, args.num_parts)
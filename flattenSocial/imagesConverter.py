import os
import sys
from PIL import Image

def convert_to_jpg(input_folder):
    # Supported image formats by Pillow
    supported_formats = {"JPEG", "JPG", "PNG", "WEBP", "HEIC", "TIFF", "BMP"}

    if not os.path.isdir(input_folder):
        print(f"Error: {input_folder} is not a valid directory.")
        sys.exit(1)

    for root, _, files in os.walk(input_folder):
        for file in files:
            file_path = os.path.join(root, file)
            file_extension = os.path.splitext(file)[1].lower()

            if file_extension not in [".jpg", ".jpeg"]:
                try:
                    with Image.open(file_path) as img:
                        if img.format.upper() in supported_formats:
                            # Convert and save as JPG
                            rgb_image = img.convert("RGB")
                            new_file_path = os.path.splitext(file_path)[0] + ".jpg"
                            rgb_image.save(new_file_path, "JPEG")
                            print(f"Converted: {file_path} -> {new_file_path}")

                            # Optionally delete the original file
                            os.remove(file_path)
                        else:
                            print(f"Unsupported format: {file_path}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_to_jpg.py <folder_path>")
        sys.exit(1)

    input_folder = sys.argv[1]
    convert_to_jpg(input_folder)

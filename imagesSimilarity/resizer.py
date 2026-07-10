import os
import sys
from PIL import Image, ImageOps

def resize_image(image_path, output_folder, target_size=(1024, 768)):
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)  # Fixes orientation issues
        img.thumbnail(target_size, Image.LANCZOS)
        
        new_img = Image.new("RGB", target_size, (0, 0, 0))  # Black padding
        x_offset = (target_size[0] - img.width) // 2
        y_offset = (target_size[1] - img.height) // 2
        new_img.paste(img, (x_offset, y_offset))
        
        output_path = os.path.join(output_folder, os.path.basename(image_path))
        new_img.save(output_path, "JPEG", quality=95)
        print(f"Resized: {image_path} -> {output_path}")
    except Exception as e:
        print(f"Error processing {image_path}: {e}")

def process_folder(folder_path, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            image_path = os.path.join(folder_path, filename)
            resize_image(image_path, output_folder)

def main():
    if len(sys.argv) != 2:
        print("Usage: python resize_images.py <folder_path>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    output_folder_name = os.path.basename(os.path.normpath(folder_path))
    output_folder = os.path.join(os.path.dirname(folder_path), output_folder_name)
    process_folder(folder_path, output_folder)
    print("Processing complete.")

if __name__ == "__main__":
    main()

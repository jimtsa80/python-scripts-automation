import os
import sys
from PIL import Image

def crop_image(image_path, x, y, width, height):
    # Open the image file
    img = Image.open(image_path)
    # Define the box to crop
    box = (x, y, x + width, y + height)
    # Crop the image
    cropped_img = img.crop(box)
    return cropped_img

def save_cropped_image(image_path, cropped_img, save_folder):
    # Ensure the save folder exists
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    
    # Get the base name of the image file and construct the save path
    base_name = os.path.basename(image_path)
    file_name, file_extension = os.path.splitext(base_name)
    save_path = os.path.join(save_folder, f"logo_{file_name}{file_extension}")
    
    # Save the cropped image
    cropped_img.save(save_path)
    print(f"Cropped image saved as {save_path}")

def process_image(image_path, x, y, width, height, save_folder='logos'):
    cropped_img = crop_image(image_path, x, y, width, height)
    save_cropped_image(image_path, cropped_img, save_folder)

def main():
    if len(sys.argv) != 6:
        print("Usage: python script.py <images_folder> <x> <y> <width> <height>")
        sys.exit(1)
    
    images_folder = sys.argv[1]
    x = int(sys.argv[2])
    y = int(sys.argv[3])
    width = int(sys.argv[4])
    height = int(sys.argv[5])
    
    # Process all images in the given folder
    for image_name in os.listdir(images_folder):
        image_path = os.path.join(images_folder, image_name)
        if os.path.isfile(image_path):
            process_image(image_path, x, y, width, height)

if __name__ == "__main__":
    main()

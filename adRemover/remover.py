import cv2
import os
import shutil
import sys

def detect_logo(image_path, logo_template, threshold=0.35, search_region=None):
    image = cv2.imread(image_path, 0)  # Read the image in grayscale
    if image is None:
        print(f"Error: Unable to load image {image_path}")
        return False, None

    if search_region:
        x, y, w, h = search_region
        cropped_image = image[y:y+h, x:x+w]
    else:
        cropped_image = image
    
    # Check if the region is smaller than the template
    if cropped_image.shape[0] < logo_template.shape[0] or cropped_image.shape[1] < logo_template.shape[1]:
        print(f"Error: Search region in image {image_path} is smaller than the template")
        return False, cropped_image

    result = cv2.matchTemplate(cropped_image, logo_template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    # Debugging: Print the max value and location
    print(f"Image: {image_path}, Max Value: {max_val}, Location: {max_loc}")

    return max_val >= threshold, cropped_image

def process_images(input_folder, logo_path, output_folder, cropped_folder, threshold=0.35, search_region=None):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    if not os.path.exists(cropped_folder):
        os.makedirs(cropped_folder)

    print(f"Loading logo template from: {logo_path}")
    logo_template = cv2.imread(logo_path, 0)
    if logo_template is None:
        print(f"Error: Unable to load logo template from {logo_path}")
        return

    print(f"Logo template size: {logo_template.shape}")

    print(f"Loading images from folder: {input_folder}")
    filenames = [f for f in os.listdir(input_folder) if os.path.isfile(os.path.join(input_folder, f))]

    print(f"Processing {len(filenames)} images...")
    for filename in filenames:
        image_path = os.path.join(input_folder, filename)
        
        match, cropped_image = detect_logo(image_path, logo_template, threshold, search_region)
        cropped_image_path = os.path.join(cropped_folder, f"cropped_{filename}")
        cv2.imwrite(cropped_image_path, cropped_image)
        
        if not match:
            print(f"Moving image {filename} to {output_folder} (logo not detected)")
            shutil.move(image_path, os.path.join(output_folder, filename))
        else:
            print(f"Logo detected in image {filename}")

    print("Processing completed.")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python script.py <input_folder> <logo_path> <output_folder> <cropped_folder>")
        sys.exit(1)

    input_folder = sys.argv[1]
    logo_path = sys.argv[2]
    output_folder = sys.argv[3]
    cropped_folder = sys.argv[4]

    print(f"Input folder: {input_folder}")
    print(f"Logo path: {logo_path}")
    print(f"Output folder: {output_folder}")
    print(f"Cropped folder: {cropped_folder}")

    # Define the search region (x, y, width, height) for the logo detection
    search_region = (1707, 54, 159, 105)  # Replace these values with the actual coordinates
    print(f"Search region: {search_region}")

    # Process the images
    process_images(input_folder, logo_path, output_folder, cropped_folder, threshold=0.35, search_region=search_region)

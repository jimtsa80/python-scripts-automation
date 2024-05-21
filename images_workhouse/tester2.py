import cv2
import numpy as np
import os

# Path to the template image
template_path = 't-mobile.jpg'
# Path to the folder containing images to search in
images_folder_path = 'test-images'
# Path to save the output images
output_folder_path = 'results-images'

# Load the template image
template = cv2.imread(template_path, 0)
if template is None:
    print(f"Failed to load the template image from {template_path}")
    exit(1)
w, h = template.shape[::-1]

# Create the output folder if it doesn't exist
os.makedirs(output_folder_path, exist_ok=True)

# Loop through all images in the folder
for filename in os.listdir(images_folder_path):
    image_path = os.path.join(images_folder_path, filename)
    image = cv2.imread(image_path)
    
    if image is None:
        print(f"Failed to load image {image_path}")
        continue
    
    # Convert the image to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply template matching
    result = cv2.matchTemplate(gray_image, template, cv2.TM_CCOEFF_NORMED)
    
    # Define a threshold
    threshold = 0.42
    loc = np.where(result >= threshold)
    
    # Check if any matches are found
    if not loc[0].size:
        print(f"No matches found in image {image_path}")
        continue
    
    # Print matching scores for diagnostic purposes
    print(f"Matches found in image {image_path} with scores: {result[loc]}")
    
    # Draw rectangles around matched regions
    for pt in zip(*loc[::-1]):
        cv2.rectangle(image, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 2)
    
    # Save the output image
    output_path = os.path.join(output_folder_path, filename)
    cv2.imwrite(output_path, image)

print("Template matching completed and images saved in the output folder.")

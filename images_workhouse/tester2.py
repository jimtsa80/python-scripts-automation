import os
from PIL import Image
import numpy as np
import cv2

def find_tmobile_logo(image_folder_path, output_csv_path, result_image_folder_path):
  """
  This function finds images containing the T-Mobile logo in a folder and creates a CSV file listing the filenames and saves the images to a new folder.

  Args:
    image_folder_path: Path to the folder containing the images.
    output_csv_path: Path to the output CSV file.
    result_image_folder_path: Path to the folder where the images containing the T-Mobile logo will be saved.
  """
  # Create the result folder if it doesn't exist
  os.makedirs(result_image_folder_path, exist_ok=True)

  # Open the output CSV file in write mode
  with open(output_csv_path, 'w') as csvfile:
    # Write the header row
    csvfile.write('filename\n')

    for filename in os.listdir(image_folder_path):
      # Get the full image path
      image_path = os.path.join(image_folder_path, filename)

      # Read the image using OpenCV
      image = cv2.imread(image_path)
      print(f"Reading image: {filename}")  # Print filename being processed

      # Check if image is read successfully
      if image is None:
          print(f"Error: Could not read image {filename}")
          continue

      # Convert the image to RGB color space (OpenCV uses BGR by default)
      image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

      try:
        # Template Matching Approach
        # Replace 'path/to/tmobile_logo_template.jpg' with the actual path to your template image
        template = cv2.imread('t-mobile.jpg')
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # If a match is found with a high confidence score, save the image
        if max_val > 0.5:
          print(f"T-Mobile logo detected in {filename} with confidence {max_val} at location {max_loc}")
          os.rename(image_path, os.path.join(result_image_folder_path, filename))
          csvfile.write(filename + '\n')

        # Color Detection Approach (alternative)
        # Define HSV color range for T-Mobile magenta (adjust values as needed)
        lower_magenta = np.array([150, 100, 100], dtype="uint8")
        upper_magenta = np.array([180, 255, 255], dtype="uint8")
        # Convert image to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # Create a mask for magenta pixels
        mask = cv2.inRange(hsv, lower_magenta, upper_magenta)
        # Count the number of magenta pixels
        num_magenta_pixels = cv2.countNonZero(mask)
        # Check if a significant portion of the image is magenta
        if num_magenta_pixels > 0.1 * image.size:
          print(f"Potential T-Mobile logo detected in {filename} (color analysis)")
          os.rename(image_path, os.path.join(result_image_folder_path, filename))
          csvfile.write(filename + '\n')

      except Exception as e:
        print(f"Error processing image {filename}: {e}")
        pass 

find_tmobile_logo('test-images', 'output.csv', 'result-images')

import cv2
import numpy as np
import os
import sys
from openpyxl import Workbook
from tqdm import tqdm
import re

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def region_histogram(image, start_row, end_row, bins):
    region = image[start_row:end_row, :]  # Slice horizontal region
    hist = cv2.calcHist([region], [0, 1, 2], None, [bins, bins, bins], [0, 256, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    return hist

def compare_image_horizontal_slices(imageA, imageB, bins=32, threshold=0.90):
    """
    Compare images by dividing them into 20 horizontal slices.
    - `bins`: Number of bins for the histogram.
    - `threshold`: Similarity threshold (0 to 1).3
    """
    height, width, _ = imageA.shape
    slice_height = height // 20  # Divide height into 15 slices

    # Compare each of the 20 horizontal slices
    for i in range(20):
        start_row = i * slice_height
        end_row = (i + 1) * slice_height if i < 19 else height  # Ensure last slice gets any remainder

        histA = region_histogram(imageA, start_row, end_row, bins)
        histB = region_histogram(imageB, start_row, end_row, bins)
        
        # Compare histograms using correlation method
        similarity = cv2.compareHist(histA, histB, cv2.HISTCMP_CORREL)
        
        if similarity < threshold:
            return similarity, False  # If any slice differs, images are dissimilar

    # If all slices are above the threshold
    return similarity, True

def compare_images_in_folder(folder_path, bins=32, threshold=0.90):
    """
    Compare each image within a folder with the next one using 20 horizontal slices histogram comparison.
    """
    image_files = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))], key=natural_sort_key)

    all_results = []
    for i in tqdm(range(len(image_files) - 1), desc="Processing images"):
        target_image_path = image_files[i]
        comparison_image_path = image_files[i + 1]

        target_image = cv2.imread(target_image_path)
        comparison_image = cv2.imread(comparison_image_path)

        if target_image is None:
            print(f"Warning: Unable to read image {target_image_path}. Skipping.")
            continue
        if comparison_image is None:
            print(f"Warning: Unable to read image {comparison_image_path}. Skipping.")
            continue

        # Compare horizontal slices using histogram comparison
        hist_similarity, hist_similar = compare_image_horizontal_slices(target_image, comparison_image, bins=bins, threshold=threshold)

        if hist_similar:
            all_results.append((target_image_path, comparison_image_path, hist_similarity))

    return all_results

def write_results_to_excel(results, folder_name):
    """
    Write comparison results to an Excel file.
    """
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Similarity Results"
        ws.append(["Target Image", "Compared Image", "Similarity Score"])

        for target_img, compared_img, similarity in results:
            ws.append([target_img, compared_img, similarity])

        output_filename = f"{folder_name}.xlsx"
        wb.save(output_filename)
        print(f"Results written to {output_filename}")
    except Exception as e:
        print(f"Error writing results to Excel: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    folder_name = os.path.basename(folder_path.rstrip('/\\'))

    # Compare with stricter bins and higher threshold
    all_results = compare_images_in_folder(folder_path, bins=32, threshold=0.90)
    write_results_to_excel(all_results, folder_name)

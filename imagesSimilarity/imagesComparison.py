import cv2
import numpy as np
import os
import sys  
from openpyxl import Workbook
from tqdm import tqdm
import re

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
'''
def compare_images_histogram(imageA, imageB):
    def region_histogram(image, start_col, end_col):
        region = image[:, start_col:end_col]
        hist = cv2.calcHist([region], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        return hist

    height, width, _ = imageA.shape
    col_width = width // 4

    columns = [
        (0, col_width),                # Left column
        (col_width, 2 * col_width),    # Left-middle column
        (2 * col_width, 3 * col_width),# Right-middle column
        (3 * col_width, width)         # Right column
    ]

    similarity_scores = []
    for start_col, end_col in columns:
        histA = region_histogram(imageA, start_col, end_col)
        histB = region_histogram(imageB, start_col, end_col)
        similarity = cv2.compareHist(histA, histB, cv2.HISTCMP_CORREL)
        similarity_scores.append(similarity)

    overall_similarity = np.mean(similarity_scores)
    return overall_similarity
'''
def compare_images_histogram(imageA, imageB):
    def region_histogram(image, start_row, end_row, start_col, end_col):
        region = image[start_row:end_row, start_col:end_col]
        hist = cv2.calcHist([region], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        return hist

    height, width, _ = imageA.shape
    row_height = height // 3
    col_width = width // 3

    regions = [
        (0, row_height, 0, col_width),                     
        (0, row_height, col_width, 2 * col_width),         
        (0, row_height, 2 * col_width, width),             
        (row_height, 2 * row_height, 0, col_width),        
        (row_height, 2 * row_height, col_width, 2 * col_width),  
        (row_height, 2 * row_height, 2 * col_width, width),
        (2 * row_height, height, 0, col_width),            
        (2 * row_height, height, col_width, 2 * col_width),
        (2 * row_height, height, 2 * col_width, width)     
    ]

    similarity_scores = []
    for start_row, end_row, start_col, end_col in regions:
        histA = region_histogram(imageA, start_row, end_row, start_col, end_col)
        histB = region_histogram(imageB, start_row, end_row, start_col, end_col)
        similarity = cv2.compareHist(histA, histB, cv2.HISTCMP_CORREL)
        similarity_scores.append(similarity)

    overall_similarity = np.mean(similarity_scores)
    return overall_similarity

def compare_images_in_folder(folder_path):
    image_files = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))], key=natural_sort_key)

    all_results = []
    for i, target_image_path in enumerate(tqdm(image_files, desc="Processing target images")):
        target_image = cv2.imread(target_image_path)
        if target_image is None:
            print(f"Warning: Unable to read image {target_image_path}. Skipping.")
            continue
        
        indices_to_compare = list(range(max(0, i - 3), min(len(image_files), i + 4)))
        indices_to_compare.remove(i)

        for idx in tqdm(indices_to_compare, desc=f"Comparing images for {os.path.basename(target_image_path)}", leave=False):
            comparison_image_path = image_files[idx]
            comparison_image = cv2.imread(comparison_image_path)
            if comparison_image is None:
                print(f"Warning: Unable to read image {comparison_image_path}. Skipping.")
                continue
            
            similarity = compare_images_histogram(target_image, comparison_image)
            all_results.append((target_image_path, comparison_image_path, similarity))

    return all_results

def write_results_to_excel(results, folder_name):
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

    all_results = compare_images_in_folder(folder_path)
    write_results_to_excel(all_results, folder_name)

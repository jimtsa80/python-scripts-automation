import cv2
import os
import sys
import openpyxl

def compare_images_histogram(imageA, imageB):
    histA = cv2.calcHist([imageA], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    histB = cv2.calcHist([imageB], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    cv2.normalize(histA, histA)
    cv2.normalize(histB, histB)
    similarity = cv2.compareHist(histA, histB, cv2.HISTCMP_CORREL)
    return similarity

def create_excel_with_similarity_and_removal(folder_path):
    image_files = sorted([os.path.join(folder_path, file) for file in os.listdir(folder_path) if file.endswith(('.png', '.jpg', '.jpeg'))])
    
    if len(image_files) < 2:
        print("Not enough images to compare.")
        return

    similarities = []
    similar_images = []

    for i in range(1, len(image_files)):
        imageA = cv2.imread(image_files[i - 1])
        imageB = cv2.imread(image_files[i])
        similarity = compare_images_histogram(imageA, imageB)
        filenameA = os.path.basename(image_files[i - 1])
        filenameB = os.path.basename(image_files[i])
        similarities.append((filenameB, similarity))

        if similarity >= 0.99:
            similar_images.append((filenameA, filenameB))

    # Create an Excel workbook and add data
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Image Similarities"
    sheet.append(["Filename", "Similarity with Previous Image", "ToRemove"])

    for filename, similarity in similarities:
        to_remove = 1 if similarity >= 0.99 else 0
        sheet.append([filename, similarity, to_remove])

    # Save the workbook with the same name as the folder
    folder_name = os.path.basename(os.path.normpath(folder_path))
    excel_filename = os.path.join(folder_name + ".xlsx")
    workbook.save(excel_filename)
    print(f"Excel file '{excel_filename}' created with similarity")

    # Print similar images
    print("\nSimilar Images (Similarity >= 0.99):")
    for img_pair in similar_images:
        print(f"{img_pair[0]} and {img_pair[1]}")

    print("\nTotal similar images with similarity >= 0.99:", len(similar_images), "out of", len(image_files), "total images")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python compare_images.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    if not os.path.exists(folder_path):
        print(f"The folder {folder_path} does not exist.")
        sys.exit(1)
    
    create_excel_with_similarity_and_removal(folder_path)

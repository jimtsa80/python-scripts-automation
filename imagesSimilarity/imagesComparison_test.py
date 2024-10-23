import os
import numpy as np
import argparse
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
from sklearn.cluster import KMeans
import cv2
import shutil
import zipfile
import openpyxl
from tqdm import tqdm
import concurrent.futures

# Load pre-trained ResNet50 model
model = ResNet50(weights='imagenet', include_top=False, pooling='max')

# Function to convert image to feature vector
def image_to_feature_vector(img_path, model):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    
    features = model.predict(img_array)
    return features.flatten()

# Function to zip a folder
def zip_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

# Function to compare images using histogram similarity
def compare_images_histogram(imageA_path, imageB_path):
    imageA = cv2.imread(imageA_path)
    imageB = cv2.imread(imageB_path)

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

# Function to compare images with a threshold check
def compare_and_check_similarity(img_pair):
    original_img_path, compare_img_path = img_pair
    similarity = compare_images_histogram(original_img_path, compare_img_path)
    return compare_img_path if similarity > 0.97 else None  # Return the similar image if above threshold

# Main function to process images, create lookup table, and aggregate folders
def process_images(image_folder):
    print(f"Processing images in folder: {image_folder}")

    # Load and process all images
    image_paths = [os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    print(f"Found {len(image_paths)} images in the folder. Converting them to feature vectors...")

    feature_vectors = []
    for img in tqdm(image_paths, desc="Loading images"):
        feature_vectors.append(image_to_feature_vector(img, model))
    
    print("Finished converting images to feature vectors.")

    # Convert list to numpy array
    feature_vectors = np.array(feature_vectors)

    # Cluster images using KMeans
    num_clusters = 5  # Adjust the number of clusters as needed
    kmeans = KMeans(n_clusters=num_clusters)
    print(f"Clustering images into {num_clusters} clusters...")
    labels = kmeans.fit_predict(feature_vectors)

    print("Finished clustering. Now processing each cluster...")

    # Prepare data for the XLSX look-up table
    output_xlsx = os.path.join(image_folder, "sequences.xlsx")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sequences"
    sheet.append(["Image Name", "Similar Images"])

    # To track copied images and avoid copying them multiple times
    copied_images = set()

    # Create a reduced folder for categorizing
    reduced_folder = os.path.join(image_folder, f"reduced_{os.path.basename(os.path.normpath(image_folder))}")
    os.makedirs(reduced_folder, exist_ok=True)

    uncategorized_images = []

    # Process images within each cluster using histogram comparison
    for cluster in range(num_clusters):
        print(f"Processing cluster {cluster+1}/{num_clusters}...")
        cluster_indices = np.where(labels == cluster)[0]
        cluster_images = [image_paths[idx] for idx in cluster_indices]

        print(f"Found {len(cluster_images)} images in this cluster.")

        # Compare each image in the cluster with others using multithreading
        for i in range(len(cluster_images)):
            original_img_path = cluster_images[i]
            
            # Skip if this image has already been copied
            if original_img_path in copied_images:
                print(f"Image {original_img_path} already copied, skipping...")
                continue
            
            similar_images = []
            
            # Use multithreading for comparisons
            with concurrent.futures.ThreadPoolExecutor() as executor:
                img_pairs = [(original_img_path, cluster_images[j]) for j in range(i+1, len(cluster_images))]
                results = list(executor.map(compare_and_check_similarity, img_pairs))

            # Filter out None values and gather similar images
            for result in results:
                if result is not None:
                    print(f"Image {original_img_path} is similar to {result}")
                    similar_images.append(result)

            # Create a subfolder for the original image if similar images are found
            if similar_images:
                # Create a folder for this image and its similar images
                similar_folder = os.path.join(reduced_folder, os.path.splitext(os.path.basename(original_img_path))[0])
                os.makedirs(similar_folder, exist_ok=True)

                # Copy the original image to the similar folder
                shutil.copy(original_img_path, os.path.join(similar_folder, os.path.basename(original_img_path)))

                # Copy all similar images to the same folder
                for sim_img in similar_images:
                    shutil.copy(sim_img, os.path.join(similar_folder, os.path.basename(sim_img)))
                    copied_images.add(sim_img)

                # Add to XLSX lookup table per cluster
                image_name = os.path.basename(original_img_path)
                similar_images_str = ', '.join([os.path.basename(sim_img) for sim_img in similar_images])
                sheet.append([image_name, similar_images_str])

            else:
                # Move uncategorized images to the reduced folder
                shutil.copy(original_img_path, os.path.join(reduced_folder, os.path.basename(original_img_path)))
                uncategorized_images.append(original_img_path)
                copied_images.add(original_img_path)
                print(f"No similar images found for {original_img_path}. Moved to reduced folder.")

        # Save the workbook after each cluster is processed
        workbook.save(output_xlsx)
        print(f"Cluster {cluster+1} processed and saved to {output_xlsx}.")

    # Zip the reduced folder
    zip_path = os.path.join(image_folder, f"reduced_{os.path.basename(image_folder)}.zip")
    print(f"Zipping reduced folder into {zip_path}...")
    zip_folder(reduced_folder, zip_path)

    # Print statistics
    initial_count = len(image_paths)
    reduced_count = len(os.listdir(reduced_folder))
    reduction_percentage = (initial_count - reduced_count) / initial_count * 100
    
    print(f"Number of images in the initial folder: {initial_count}")
    print(f"Number of images in the reduced folder: {reduced_count}")
    print(f"Percentage of reduction: {reduction_percentage:.2f}%")

if __name__ == '__main__':
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Sort images based on similarity and generate sequences.')
    parser.add_argument('folder', type=str, help='Path to the folder containing images')

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the function with the provided folder
    process_images(args.folder)

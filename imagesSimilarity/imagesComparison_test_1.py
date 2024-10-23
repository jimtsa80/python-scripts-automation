import os
import numpy as np
import argparse
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
from sklearn.cluster import KMeans
import cv2
import shutil
import zipfile
import openpyxl
from tqdm import tqdm
from annoy import AnnoyIndex

# Pre-compute features for faster lookup (optional)
def precompute_features(image_folder, model):
    features_db = {}
    for image_path in sorted([os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]):
        img = image.load_img(image_path, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        features = model.predict(img_array)
        features_db[image_path] = features.flatten()
    return features_db

# Load pre-trained ResNet50 model
model = EfficientNetB0(weights='imagenet', include_top=False, pooling='max')

# Function to convert image to feature vector
def image_to_feature_vector(img_path, model, precomputed_features=None):
    if precomputed_features and img_path in precomputed_features:
        return precomputed_features[img_path]

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
            for file in sorted(files):  # Sort files for consistent zipping
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

# Use Approximate Nearest Neighbors (ANN) for efficient similarity search
def build_ann_index(features_db, metric='euclidean', n_trees=30):
    index = AnnoyIndex(features_db[list(features_db.keys())[0]].shape[0], metric=metric)
    for i, (image_path, features) in enumerate(features_db.items()):
        index.add_item(i, features)
    index.build(n_trees)
    return index

def find_similar_images(index, query_features, cluster_images, all_image_paths, n_neighbors=30):
    similar_indices = index.get_nns_by_vector(query_features, n_neighbors)

    # Map similar indices from the ANN index back to the correct images in cluster_images
    cluster_indices = [all_image_paths.index(img) for img in cluster_images]

    # Filter out indices that correspond to the current cluster only
    valid_similar_indices = [i for i in similar_indices if i in cluster_indices]
    
    # Map back to the cluster images
    return [all_image_paths[i] for i in valid_similar_indices]

# Histogram-based similarity comparison
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

# Main function to process images
def process_images(image_folder):
    print(f"Processing images in folder: {image_folder}")

    # Step 1: Gather image paths
    image_paths = [os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    print(f"Found {len(image_paths)} images in the folder.")
    initial_count = len(image_paths)  # Count of initial images

    # Step 2: Precompute features
    print("Precomputing image features...")
    precomputed_features = precompute_features(image_folder, model)
    print("Features precomputation completed.")

    # Step 3: Convert images to feature vectors
    print("Converting images to feature vectors...")
    feature_vectors = [image_to_feature_vector(img, model, precomputed_features) for img in tqdm(image_paths, desc="Loading images")]
    print("Feature vector conversion completed.")

    feature_vectors = np.array(feature_vectors)
    num_clusters = 5
    print(f"Clustering images into {num_clusters} clusters...")
    kmeans = KMeans(n_clusters=num_clusters)
    labels = kmeans.fit_predict(feature_vectors)
    print("Clustering completed.")

    # Step 4: Set up output files
    output_xlsx = os.path.join(image_folder, "sequences.xlsx")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sequences"
    sheet.append(["Image Name", "Similar Images"])

    copied_images = set()
    reduced_folder = os.path.join(image_folder, f"reduced_{os.path.basename(os.path.normpath(image_folder))}")
    os.makedirs(reduced_folder, exist_ok=True)

    sequence_folder = os.path.join(image_folder, "all_sequences")  # New folder for all sequences
    os.makedirs(sequence_folder, exist_ok=True)

    uncategorized_images = []
    processed_images = set()  # Track all processed images
    first_images_of_sequences = []  # To store the first images of each sequence

    # Step 5: Iterate through clusters
    for cluster in range(num_clusters):
        print(f"Processing cluster {cluster + 1}/{num_clusters}...")
        cluster_indices = np.where(labels == cluster)[0]
        cluster_images = [image_paths[idx] for idx in cluster_indices]

        ann_index = build_ann_index(precomputed_features, metric='euclidean')
        
        for i in range(len(cluster_images)):
            original_img_path = cluster_images[i]

            if original_img_path in processed_images:
                continue

            query_features = precomputed_features[original_img_path]
            similar_images = find_similar_images(ann_index, query_features, cluster_images, image_paths, n_neighbors=10)

            filtered_similar_images = []
            for sim_img_path in similar_images:
                similarity = compare_images_histogram(original_img_path, sim_img_path)
                if similarity > 0.999:
                    filtered_similar_images.append(sim_img_path)

            similar_images = filtered_similar_images

            # Check for similar images
            if similar_images and len(similar_images) > 1:  # Check if there are more than 2 similar images
                print(f"Found {len(similar_images)} similar images for {os.path.basename(original_img_path)}.")
                similar_folder = os.path.join(sequence_folder, os.path.splitext(os.path.basename(original_img_path))[0])
                os.makedirs(similar_folder, exist_ok=True)

                # Copy the original image as the first image of the sequence
                shutil.copy(original_img_path, os.path.join(similar_folder, os.path.basename(original_img_path)))
                first_images_of_sequences.append(original_img_path)  # Store the first image of the sequence

                for sim_img in similar_images:
                    if sim_img not in processed_images:
                        shutil.copy(sim_img, os.path.join(similar_folder, os.path.basename(sim_img)))
                        copied_images.add(sim_img)

                image_name = os.path.basename(original_img_path)
                similar_images_str = ', '.join([os.path.basename(sim_img) for sim_img in similar_images if sim_img not in processed_images])
                sheet.append([image_name, similar_images_str])
                processed_images.update(similar_images)

            else:
                print(f"No similar images found for {os.path.basename(original_img_path)}. Copying to reduced folder.")
                # If no similar images, just copy to reduced folder
                shutil.copy(original_img_path, os.path.join(reduced_folder, os.path.basename(original_img_path)))
                uncategorized_images.append(original_img_path)
                copied_images.add(original_img_path)

    # Step 6: Copy the first images of each sequence to the reduced folder
    print("Copying first images of sequences to the reduced folder...")
    for first_image in first_images_of_sequences:
        shutil.copy(first_image, os.path.join(reduced_folder, os.path.basename(first_image)))

    # Step 7: Save output and final statistics
    workbook.save(output_xlsx)
    print(f"Sequences saved to {output_xlsx}.")

    # Final statistics
    num_images_in_reduced_folder = len([f for f in os.listdir(reduced_folder) if f.endswith(('.png', '.jpg', '.jpeg'))])
    reduction_percentage = ((initial_count - num_images_in_reduced_folder) / initial_count) * 100 if initial_count > 0 else 0

    print(f"Initial count of images: {initial_count}")
    print(f"Count of images in reduced folder: {num_images_in_reduced_folder}")
    print(f"Reduction percentage: {reduction_percentage:.2f}%")

    # Create a zip of the reduced folder
    zip_path = os.path.join(image_folder, f"reduced_{os.path.basename(os.path.normpath(image_folder))}.zip")
    zip_folder(reduced_folder, zip_path)

    print(f"Reduced images are zipped and stored at: {zip_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find and cluster similar images.")
    parser.add_argument("image_folder", type=str, help="Path to the folder containing images.")
    args = parser.parse_args()

    process_images(args.image_folder)

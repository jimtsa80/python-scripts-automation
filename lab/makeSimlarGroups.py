import cv2
import os
import shutil
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from torchvision import models, transforms
from PIL import Image
import torch
from tqdm import tqdm

def load_images_from_folder(folder):
    """Load image file paths from the given folder."""
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(('jpg', 'jpeg', 'png'))]

def extract_features(image_paths):
    """Extract deep features using EfficientNet-B3 for higher accuracy."""
    model = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.DEFAULT)
    model = torch.nn.Sequential(*(list(model.children())[:-1]))  # Remove final classification layer
    model.eval()

    transform = transforms.Compose([
        transforms.Resize((384, 384)),  # Higher resolution for better feature extraction
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    features = []
    for image_path in tqdm(image_paths, desc="Extracting features"):
        img = Image.open(image_path).convert('RGB')
        img = transform(img).unsqueeze(0)
        with torch.no_grad():
            feat = model(img).squeeze().numpy()
        features.append(feat.flatten())
    return np.array(features)

def find_similar_images(folder, output_csv="image_features.csv"):
    """Extract features and save them to a CSV file."""
    images = load_images_from_folder(folder)
    features = extract_features(images)
    df = pd.DataFrame(features)
    df.insert(0, 'Image', images)
    df.to_csv(output_csv, index=False)
    return output_csv, len(images)

def compute_cosine_distance_matrix(feature_vectors, batch_size=500):
    """Compute cosine distance matrix in chunks to avoid memory issues."""
    num_images = feature_vectors.shape[0]
    cosine_distance_matrix = np.zeros((num_images, num_images), dtype=np.float32)
    
    for i in range(0, num_images, batch_size):
        end_i = min(i + batch_size, num_images)
        for j in range(0, num_images, batch_size):
            end_j = min(j + batch_size, num_images)
            similarity_chunk = cosine_similarity(feature_vectors[i:end_i], feature_vectors[j:end_j])
            cosine_distance_matrix[i:end_i, j:end_j] = 1 - similarity_chunk
    
    return np.maximum(cosine_distance_matrix, 0)  # Ensure non-negative values

def cluster_images(feature_csv, source_folder, initial_count, eps=0.05, min_samples=2):
    """Cluster images using DBSCAN with stricter settings."""
    df = pd.read_csv(feature_csv)
    image_paths = df['Image'].values
    feature_vectors = df.drop(columns=['Image']).values

    try:
        cosine_distance_matrix = compute_cosine_distance_matrix(feature_vectors)
    except MemoryError:
        print("⚠️ Memory Error: Not enough RAM to compute the similarity matrix. Try reducing the number of images or using a different clustering approach.")
        return

    # DBSCAN clustering
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='precomputed').fit(cosine_distance_matrix)
    labels = clustering.labels_

    # Create output directory at the same level as the source folder
    output_folder = f"{source_folder}_similar_images"
    os.makedirs(output_folder, exist_ok=True)

    # Dictionary to track clusters
    clusters = {}
    total_moved = 0

    for img, lbl in zip(image_paths, labels):
        if lbl == -1:
            continue  # Skip noise points
        if lbl not in clusters:
            clusters[lbl] = []
        clusters[lbl].append(img)

    # Move similar images and keep track
    cluster_data = []
    for cluster_id, images in clusters.items():
        representative_image = os.path.basename(images[0])  # Keep the first image in the source folder
        similar_images = [os.path.basename(img) for img in images[1:]]  # Move all others
        total_moved += len(similar_images)
        for img in images[1:]:
            shutil.move(img, os.path.join(output_folder, os.path.basename(img)))
        cluster_data.append([representative_image, ", ".join(similar_images)])

    # Save tracking info in Excel
    df_cluster_info = pd.DataFrame(cluster_data, columns=["Representative Image", "Similar Images"])
    df_cluster_info.to_excel(os.path.join(output_folder, "similar_images_info.xlsx"), index=False)

    final_count = initial_count - total_moved
    reduction_percentage = (total_moved / initial_count) * 100

    print(f"Clusters created in '{output_folder}' with tracking info saved.")
    print(f"Total images moved: {total_moved}")
    print(f"Initial images: {initial_count}, Remaining images: {final_count}")
    print(f"Reduction percentage: {reduction_percentage:.2f}%")

def main(image_folder):
    output_csv = "image_features.csv"
    print("📌 Step 1: Extracting Features...")
    feature_csv, initial_count = find_similar_images(image_folder, output_csv)
    print("📌 Step 2: Clustering and moving similar images...")
    cluster_images(feature_csv, image_folder, initial_count)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Find and cluster similar images.")
    parser.add_argument("image_folder", type=str, help="Path to the folder containing images")
    args = parser.parse_args()
    main(args.image_folder)
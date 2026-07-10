import os
import numpy as np
import argparse
import shutil
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from tqdm import tqdm
import matplotlib.pyplot as plt

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

# Function to determine optimal clusters
def determine_optimal_clusters(image_folder, max_clusters=10, use_dbscan=False):
    image_paths = [os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    print("Extracting features from images...")
    feature_vectors = [image_to_feature_vector(img, model) for img in tqdm(image_paths, desc="Processing images")]
    feature_vectors = np.array(feature_vectors)
    
    # Reduce dimensions using PCA
    print("Applying PCA for dimensionality reduction...")
    pca = PCA(n_components=50, random_state=42)
    feature_vectors_reduced = pca.fit_transform(feature_vectors)
    
    if use_dbscan:
        print("Applying DBSCAN clustering...")
        dbscan = DBSCAN(eps=5, min_samples=5)  # Adjust eps based on data
        labels = dbscan.fit_predict(feature_vectors_reduced)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        print(f"Estimated clusters with DBSCAN: {n_clusters}")
        save_clustered_images(image_paths, labels)
        return labels
    
    # K-means clustering
    silhouette_scores = []
    wcss = []
    cluster_range = range(2, max_clusters + 1)
    
    print("Evaluating optimal number of clusters...")
    for n_clusters in tqdm(cluster_range, desc="Testing clusters"):
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(feature_vectors_reduced)
        wcss.append(kmeans.inertia_)
        score = silhouette_score(feature_vectors_reduced, labels)
        silhouette_scores.append(score)
    
    # Plot silhouette scores
    plt.figure(figsize=(10, 6))
    plt.plot(cluster_range, silhouette_scores, marker='o')
    plt.title("Silhouette Scores for Different Cluster Numbers")
    plt.xlabel("Number of Clusters")
    plt.ylabel("Silhouette Score")
    plt.grid()
    plt.show()
    
    # Plot Elbow Method (WCSS)
    plt.figure(figsize=(10, 6))
    plt.plot(cluster_range, wcss, marker='o')
    plt.title("Elbow Method for Optimal Clusters")
    plt.xlabel("Number of Clusters")
    plt.ylabel("WCSS (Within-Cluster Sum of Squares)")
    plt.grid()
    plt.show()
    
    optimal_clusters = cluster_range[np.argmax(silhouette_scores)]
    print(f"Optimal number of clusters: {optimal_clusters}")
    
    # Apply K-means with optimal k
    kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
    final_labels = kmeans.fit_predict(feature_vectors_reduced)
    save_clustered_images(image_paths, final_labels)
    return final_labels

# Function to save clustered images for verification
def save_clustered_images(image_paths, labels, output_dir="clustered_images"):
    os.makedirs(output_dir, exist_ok=True)
    for i, img_path in enumerate(image_paths):
        cluster_folder = os.path.join(output_dir, f"cluster_{labels[i]}")
        os.makedirs(cluster_folder, exist_ok=True)
        shutil.copy(img_path, cluster_folder)
    print(f"Clustered images saved in '{output_dir}'")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Determine the optimal number of clusters for image similarity.')
    parser.add_argument('folder', type=str, help='Path to the folder containing images')
    parser.add_argument('--max_clusters', type=int, default=10, help='Maximum number of clusters to evaluate')
    parser.add_argument('--dbscan', action='store_true', help='Use DBSCAN instead of K-Means')
    
    args = parser.parse_args()
    determine_optimal_clusters(args.folder, args.max_clusters, args.dbscan)

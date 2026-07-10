import cv2
import os
import shutil
import numpy as np
import pandas as pd
import zipfile
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from torchvision import models, transforms
from PIL import Image
import torch
from tqdm import tqdm

def load_images_from_folder(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(('jpg', 'jpeg', 'png'))]

def extract_features(image_paths):
    model = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.DEFAULT)
    model = torch.nn.Sequential(*(list(model.children())[:-1]))
    model.eval()

    transform = transforms.Compose([
        transforms.Resize((384, 384)),
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

def compute_cosine_distance_matrix(feature_vectors, batch_size=500):
    num_images = feature_vectors.shape[0]
    cosine_distance_matrix = np.zeros((num_images, num_images), dtype=np.float32)
    
    for i in range(0, num_images, batch_size):
        end_i = min(i + batch_size, num_images)
        for j in range(0, num_images, batch_size):
            end_j = min(j + batch_size, num_images)
            similarity_chunk = cosine_similarity(feature_vectors[i:end_i], feature_vectors[j:end_j])
            cosine_distance_matrix[i:end_i, j:end_j] = 1 - similarity_chunk
    
    return np.maximum(cosine_distance_matrix, 0)

def find_similar_images(folder):
    output_csv = os.path.join(folder, "image_features.csv")
    images = load_images_from_folder(folder)
    features = extract_features(images)
    df = pd.DataFrame(features)
    df.insert(0, 'Image', images)
    df.to_csv(output_csv, index=False)
    return output_csv, len(images)

def create_cluster_mosaic(cluster_dir, output_path, images_per_row=4):
    images = load_images_from_folder(cluster_dir)
    img_list = [cv2.imread(img) for img in images]
    if not img_list:
        return
    
    target_size = (150, 150)  # Adjust as needed
    img_list = [cv2.resize(img, target_size) for img in img_list]
    
    num_images = len(img_list)
    num_rows = (num_images + images_per_row - 1) // images_per_row
    
    mosaic_height = num_rows * target_size[1]
    mosaic_width = min(num_images, images_per_row) * target_size[0]
    mosaic = np.zeros((mosaic_height, mosaic_width, 3), dtype=np.uint8)
    
    for idx, img in enumerate(img_list):
        row = idx // images_per_row
        col = idx % images_per_row
        y, x = row * target_size[1], col * target_size[0]
        mosaic[y:y + target_size[1], x:x + target_size[0]] = img

    cv2.imwrite(output_path, mosaic)

def cluster_images(feature_csv, source_folder, initial_count, eps=0.04, min_samples=3):
    df = pd.read_csv(feature_csv)
    image_paths = df['Image'].values
    feature_vectors = df.drop(columns=['Image']).values
    
    try:
        cosine_distance_matrix = compute_cosine_distance_matrix(feature_vectors)
    except MemoryError:
        print("⚠️ Memory Error: Try reducing the number of images or using a different approach.")
        return
    
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='precomputed').fit(cosine_distance_matrix)
    labels = clustering.labels_

    output_folder = f"{source_folder}_similar_images"
    os.makedirs(output_folder, exist_ok=True)
    mosaic_folder = os.path.join(output_folder, "cluster_mosaics")
    os.makedirs(mosaic_folder, exist_ok=True)

    clusters = {}
    total_moved = 0

    for img, lbl in zip(image_paths, labels):
        if lbl == -1:
            continue  # Skip noise points
        if lbl not in clusters:
            clusters[lbl] = []
        clusters[lbl].append(img)

    cluster_data = []
    for cluster_id, images in clusters.items():
        cluster_dir = os.path.join(output_folder, f"cluster_{cluster_id}")
        os.makedirs(cluster_dir, exist_ok=True)
        representative_image = os.path.basename(images[0])
        similar_images = [os.path.basename(img) for img in images[1:]]
        total_moved += len(similar_images)
        for img in images[1:]:
            shutil.move(img, os.path.join(cluster_dir, os.path.basename(img)))
        cluster_data.append([representative_image, ", ".join(similar_images)])
        
        mosaic_path = os.path.join(mosaic_folder, f"cluster_{cluster_id}.jpg")
        create_cluster_mosaic(cluster_dir, mosaic_path)

    df_cluster_info = pd.DataFrame(cluster_data, columns=["Representative Image", "Similar Images"])
    df_cluster_info.to_excel(os.path.join(output_folder, "similar_images_info.xlsx"), index=False)
    
    final_count = initial_count - total_moved
    reduction_percentage = (total_moved / initial_count) * 100

    print(f"Clusters created in '{output_folder}' with tracking info saved.")
    print(f"Total images moved: {total_moved}")
    print(f"Initial images: {initial_count}, Remaining images: {final_count}")
    print(f"Reduction percentage: {reduction_percentage:.2f}%")
    
    return final_count

def zip_remaining_images(source_folder):
    remaining_folder = f"reduced_{os.path.basename(source_folder)}"
    reduced_path = os.path.join(os.path.dirname(source_folder), remaining_folder)
    os.makedirs(reduced_path, exist_ok=True)
    
    remaining_images = load_images_from_folder(source_folder)
    if not remaining_images:
        print("No remaining images to zip.")
        return
    
    for img in remaining_images:
        shutil.move(img, os.path.join(reduced_path, os.path.basename(img)))
    
    zip_path = os.path.join(os.path.dirname(source_folder), f"{remaining_folder}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for img in load_images_from_folder(reduced_path):
            zipf.write(img, os.path.basename(img))
    print(f"Remaining images zipped at: {zip_path}")

def main(image_folder):
    print("📌 Step 1: Extracting Features...")
    feature_csv, initial_count = find_similar_images(image_folder)
    print("📌 Step 2: Clustering and moving similar images...")
    remaining_count = cluster_images(feature_csv, image_folder, initial_count)
    # ----- DELETE THE CSV FILE NOW -----
    if os.path.exists(feature_csv):
        os.remove(feature_csv)
        print(f"Deleted temporary feature file: {feature_csv}")
    print("📌 Step 3: Zipping remaining images...")
    zip_remaining_images(image_folder)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Find and cluster similar images.")
    parser.add_argument("image_folder", type=str, help="Path to the folder containing images")
    args = parser.parse_args()
    main(args.image_folder)

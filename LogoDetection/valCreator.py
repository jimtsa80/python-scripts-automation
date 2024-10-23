import os
import random
import shutil
from pathlib import Path

def split_dataset(image_folder, label_folder, output_folder, train_ratio=0.8):
    """
    Splits a dataset into training and validation sets based on a given ratio, moving both images and labels.

    :param image_folder: Path to the folder containing all images.
    :param label_folder: Path to the folder containing all labels (in YOLO format).
    :param output_folder: Path to the output folder to store the train/val folders.
    :param train_ratio: Ratio of images to keep in the training set (default is 0.8).
    """
    # Ensure the output folders exist
    train_image_folder = Path(output_folder) / 'train' / 'images'
    train_label_folder = Path(output_folder) / 'train' / 'labels'
    val_image_folder = Path(output_folder) / 'val' / 'images'
    val_label_folder = Path(output_folder) / 'val' / 'labels'

    train_image_folder.mkdir(parents=True, exist_ok=True)
    train_label_folder.mkdir(parents=True, exist_ok=True)
    val_image_folder.mkdir(parents=True, exist_ok=True)
    val_label_folder.mkdir(parents=True, exist_ok=True)

    # Get a list of all images in the image folder
    images = list(Path(image_folder).glob('*.*'))  # Adjust if your images are of specific types (e.g., '*.jpg')

    # Shuffle the images to ensure random selection
    random.shuffle(images)

    # Determine the split point
    train_count = int(len(images) * train_ratio)
    
    # Split the dataset
    train_images = images[:train_count]
    val_images = images[train_count:]

    # Function to get corresponding label path
    def get_label_path(image_path):
        return Path(label_folder) / f"{image_path.stem}.txt"

    # Move the images and labels to their respective folders
    for img in train_images:
        label_path = get_label_path(img)
        if label_path.exists():
            shutil.copy(img, train_image_folder / img.name)
            shutil.copy(label_path, train_label_folder / label_path.name)

    for img in val_images:
        label_path = get_label_path(img)
        if label_path.exists():
            shutil.copy(img, val_image_folder / img.name)
            shutil.copy(label_path, val_label_folder / label_path.name)

    print(f"Total images: {len(images)}")
    print(f"Training set: {len(train_images)} images")
    print(f"Validation set: {len(val_images)} images")
    print(f"Images and labels have been split and copied to '{output_folder}'.")

# Example usage:
image_folder = r'C:\\Users\\jimtsa\\Desktop\\python-scripts-automation\\LogoDetection\\dataset_20240826_PacificNationsCup_Group_Canda_vs_Japan_0700_filtered\\train\\images'
label_folder = r'C:\\Users\\jimtsa\\Desktop\\python-scripts-automation\\LogoDetection\\dataset_20240826_PacificNationsCup_Group_Canda_vs_Japan_0700_filtered\\train\\labels'  # Replace with your folder containing the labels
output_folder = r'C:\\Users\\jimtsa\\Desktop\\python-scripts-automation\\LogoDetection\\dataset_20240826_PacificNationsCup_Group_Canda_vs_Japan_0700_filtered\\val'  # Replace with your desired output folder

split_dataset(image_folder, label_folder, output_folder)

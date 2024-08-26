import pandas as pd
import numpy as np
import os
import shutil
import sys
import zipfile

def main(images_folder, excel_file):
    # Load the data from the Excel file
    df = pd.read_excel(excel_file)

    # Replace NaNs or infinite values with zeros
    df['Similarity Score'] = df['Similarity Score'].replace([np.inf, -np.inf], np.nan).fillna(0)

    # Similarity threshold
    similarity_threshold = 0.98

    # Initialize variables to store sequences
    sequences = []
    current_sequence = []

    # Flatten the similarity matrix to simplify the comparison
    similarity_dict = {(row['Target Image'], row['Compared Image']): row['Similarity Score'] for index, row in df.iterrows()}

    # Get the list of target images in the order they appear
    target_images = df['Target Image'].unique()

    # Iterate through each image to find contiguous sequences
    for i in range(len(target_images)):
        target_image = target_images[i]
        
        if not current_sequence:
            current_sequence.append(target_image)
        else:
            last_image = current_sequence[-1]
            if (last_image, target_image) in similarity_dict and similarity_dict[(last_image, target_image)] >= similarity_threshold:
                current_sequence.append(target_image)
            else:
                if len(current_sequence) > 1:
                    sequences.append(current_sequence)
                current_sequence = [target_image]

    # Add the last sequence if it exists
    if len(current_sequence) > 1:
        sequences.append(current_sequence)

    total_moved_files = 0
    sequence_folders = []

    # Count the total number of files in the initial folder
    initial_file_count = len([f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f))])

    # Move images in each sequence to the target folder
    for i, sequence in enumerate(sequences):
        sequence_folder = os.path.join(images_folder, f"Sequence_{i + 1}")
        os.makedirs(sequence_folder, exist_ok=True)
        sequence_folders.append(sequence_folder)
        for image_path in sequence:
            shutil.move(os.path.join(images_folder, os.path.basename(image_path)), sequence_folder)
        num_images = len(sequence)
        total_moved_files += num_images
        print(f"Moved {num_images} images to {sequence_folder}")

    print(f"Total number of moved files: {total_moved_files}")
    print(f"Number of sequence folders created: {len(sequences)}")

    # Create new folder for remaining images and the first image of each sequence
    new_folder = os.path.join(images_folder, "reduced_" + os.path.basename(images_folder))
    os.makedirs(new_folder, exist_ok=True)

    # Copy the first image of each sequence to the new folder
    for sequence_folder in sequence_folders:
        first_image = os.listdir(sequence_folder)[0]
        shutil.copy(os.path.join(sequence_folder, first_image), new_folder)

    # Move remaining images to the new folder
    remaining_images = [f for f in os.listdir(images_folder) if os.path.isfile(os.path.join(images_folder, f))]
    for image in remaining_images:
        shutil.move(os.path.join(images_folder, image), new_folder)

    # Count the total number of files in the new folder
    new_folder_file_count = len([f for f in os.listdir(new_folder) if os.path.isfile(os.path.join(new_folder, f))])

    # Create Excel file for sequences
    sequence_data = []
    for sequence_folder in sequence_folders:
        sequence_images = os.listdir(sequence_folder)
        first_image = sequence_images[0]
        num_images = len(sequence_images)
        sequence_data.append([first_image, num_images])

    sequence_df = pd.DataFrame(sequence_data, columns=['First Image', 'Number of Images'])

    # Save the Excel file one folder outside the new_folder
    parent_folder = os.path.dirname(new_folder)
    sequence_excel_path = os.path.join(parent_folder, "sequences_info.xlsx")
    sequence_df.to_excel(sequence_excel_path, index=False)
    print(f"Created Excel file with sequence information at {sequence_excel_path}")

    # Zip the new_folder
    shutil.make_archive(new_folder, 'zip', new_folder)
    print(f"Zipped the new folder into {new_folder}.zip")

    # Calculate and print the percentage reduction
    reduction_percentage = ((initial_file_count - new_folder_file_count) / initial_file_count) * 100
    print(f"Initial folder contained {initial_file_count} files.")
    print(f"New folder contains {new_folder_file_count} files.")
    print(f"Percentage of files reduced: {reduction_percentage:.2f}%")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <images_folder> <excel_file>")
    else:
        images_folder = sys.argv[1]
        excel_file = sys.argv[2]
        main(images_folder, excel_file)

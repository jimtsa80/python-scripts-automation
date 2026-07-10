import os
import sys
import shutil
import pandas as pd
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

def classify_images_in_folders(root_folder):
    # Initialize BLIP model and processor
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

    # Prepare path for useful_video folder
    useful_video_folder = os.path.join(root_folder, "useful_video")
    os.makedirs(useful_video_folder, exist_ok=True)

    # Iterate through each subfolder
    for folder_name in os.listdir(root_folder):
        folder_path = os.path.join(root_folder, folder_name)
        if os.path.isdir(folder_path):
            results = []  # Store captions for this folder

            # Get the first 5 image files in the folder
            image_files = [
                f for f in os.listdir(folder_path)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
            ]
            image_files = sorted(image_files)[:5]  # Sort and take the first 5

            # Process each image
            print(f"\nProcessing folder: {folder_name}")
            for image_file in image_files:
                image_path = os.path.join(folder_path, image_file)
                try:
                    # Open image
                    image = Image.open(image_path).convert("RGB")

                    # Prepare inputs for BLIP
                    inputs = processor(images=image, return_tensors="pt")

                    # Generate caption
                    caption = model.generate(**inputs)
                    caption_text = processor.decode(caption[0], skip_special_tokens=True)

                    # Print the generated caption
                    print(f"  Image: {image_file} -> Caption: {caption_text}")

                    # Append result
                    results.append({
                        "Folder Name": folder_name,
                        "Image Name": image_file,
                        "Caption": caption_text
                    })
                except Exception as e:
                    print(f"  Error processing {image_file}: {e}")

            # Check if any caption contains "tennis" or "court"
            if any("tennis" in result["Caption"].lower() or "court" in result["Caption"].lower() for result in results):
                # Move the folder to useful_video
                new_folder_path = os.path.join(useful_video_folder, folder_name)
                shutil.move(folder_path, new_folder_path)
                print(f"  Moved folder: {folder_name} to {useful_video_folder}")

            # Save results to CSV in the same folder as images
            output_csv_path = os.path.join(folder_path if os.path.exists(folder_path) else new_folder_path, "output.csv")
            df = pd.DataFrame(results)
            df.to_csv(output_csv_path, index=False)
            print(f"  Results written to {output_csv_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <root_folder>")
        sys.exit(1)

    root_folder = sys.argv[1]
    classify_images_in_folders(root_folder)

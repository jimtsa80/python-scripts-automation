import os
import cv2
import torch
from ultralytics import YOLO
from transformers import CLIPProcessor, CLIPModel
from PIL import Image

# Initialize YOLOv8 and CLIP models
yolo_model = YOLO("yolov8x.pt")  # Replace with your YOLOv8 model (e.g., 'yolov8x.pt' for better accuracy)
clip_model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")  # Larger CLIP model for better feature extraction
processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")

# Define the output folder name (always the same)
output_folder = "output_detected"

# Function to process images in a folder
def process_images(input_folder, output_folder, text_descriptions, clip_threshold=0.75, yolo_threshold=0.2):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_name in os.listdir(input_folder):
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(input_folder, file_name)
            process_image(image_path, output_folder, text_descriptions, clip_threshold, yolo_threshold)

def process_image(image_path, output_folder, text_descriptions, clip_threshold, yolo_threshold):
    print(f"Processing image: {image_path}")

    # Load the image
    image = Image.open(image_path)
    cv2_image = cv2.imread(image_path)
    h, w, _ = cv2_image.shape

    # Use YOLOv8 for object detection
    results = yolo_model(image_path)
    detections = results[0].boxes.data.cpu().numpy()  # Access YOLOv8 detection results

    best_score = 0
    best_box = None
    for box in detections:
        x1, y1, x2, y2, conf, cls = box
        if conf < yolo_threshold:  # Filter low-confidence YOLO detections
            continue

        # Extract cropped region for CLIP
        cropped_image_cv2 = cv2_image[int(y1):int(y2), int(x1):int(x2)]
        if cropped_image_cv2.size == 0:  # Skip invalid crops
            continue

        # Predict with CLIP
        cropped_image_pil = Image.fromarray(cropped_image_cv2)
        inputs = processor(text=text_descriptions, images=cropped_image_pil, return_tensors="pt", padding=True)
        outputs = clip_model(**inputs)
        logits = outputs.logits_per_image
        clip_score = logits.softmax(dim=1).detach().numpy().max()

        print(f"CLIP score: {clip_score:.2f} for box {box[:4]}")

        # If CLIP score is higher than threshold, update best score and bounding box
        if clip_score > clip_threshold and clip_score > best_score:
            best_score = clip_score
            best_box = (int(x1), int(y1), int(x2), int(y2))

    # Save results if a logo is detected
    if best_box:
        print(f"Detected logo with score {best_score:.2f}. Saving results.")
        x1, y1, x2, y2 = best_box

        # Draw bounding box on the image
        cv2.rectangle(cv2_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(cv2_image, f"Score: {best_score:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Save the modified image to the output folder
        output_image_path = os.path.join(output_folder, os.path.basename(image_path))
        cv2.imwrite(output_image_path, cv2_image)

        # Write YOLO-style coordinates to a text file
        x_center = ((x1 + x2) / 2) / w
        y_center = ((y1 + y2) / 2) / h
        bbox_width = (x2 - x1) / w
        bbox_height = (y2 - y1) / h

        yolo_annotation = f"0 {x_center:.6f} {y_center:.6f} {bbox_width:.6f} {bbox_height:.6f}"
        output_txt_path = os.path.join(output_folder, os.path.splitext(os.path.basename(image_path))[0] + '.txt')

        with open(output_txt_path, 'w') as f:
            f.write(yolo_annotation)
    else:
        print(f"No logo detected in image: {image_path}")


# Main function
if __name__ == "__main__":
    # Get the input folder from command-line arguments
    import sys
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_folder>")
        sys.exit(1)

    input_folder = sys.argv[1]

    # Define the text descriptions for logos
    text_descriptions = [
        "Toyota logo"
    ]

    # Process the input folder
    process_images(input_folder, output_folder, text_descriptions)

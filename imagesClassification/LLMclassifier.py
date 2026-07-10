import os
import sys
import shutil
from PIL import Image
import torch
from transformers import (
    BlipProcessor,
    BlipForConditionalGeneration,
    GPTNeoForCausalLM,
    GPT2Tokenizer,
)
import pytesseract
import re
import csv

# Set up pytesseract for OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

def sanitize_text(text):
    # Remove any extra whitespace, newlines, and tabs
    text = text.replace("\n", " ").replace("\r", "")  # Replace newlines with a space
    text = text.replace("\t", " ")  # Replace tabs with a space
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = text.strip()  # Remove leading and trailing spaces
    return text.lower()  # Return in lowercase for case-insensitive matching

# Initialize GPT model
def initialize_gpt_model():
    try:
        tokenizer = GPT2Tokenizer.from_pretrained("EleutherAI/gpt-neo-1.3B")
        model = GPTNeoForCausalLM.from_pretrained("EleutherAI/gpt-neo-1.3B")

        # Add pad_token if not present
        if tokenizer.pad_token is None:
            tokenizer.add_special_tokens({"pad_token": "[PAD]"})
            model.resize_token_embeddings(len(tokenizer))

        model.eval()  # Set to evaluation mode
        return model, tokenizer
    except Exception as e:
        print(f"Error initializing GPT model: {e}")
        sys.exit(1)

# Initialize BLIP model for image captioning
def initialize_blip_model():
    try:
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        return processor, model
    except Exception as e:
        print(f"Error initializing BLIP model: {e}")
        sys.exit(1)

# Generate a caption for an image
def generate_caption(processor, model, image_path):
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(image, return_tensors="pt")
        with torch.no_grad():
            output = model.generate(**inputs)
        return processor.decode(output[0], skip_special_tokens=True)
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

# Extract OCR text from an image
def extract_ocr_text(image_path):
    try:
        image = Image.open(image_path).convert("RGB")
        return pytesseract.image_to_string(image)
    except Exception as e:
        print(f"Error extracting OCR from {image_path}: {e}")
        return ""

# Use GPT to classify if the image is related to horse racing
def is_related_to_horse_racing(caption, ocr_text, model, tokenizer):
    try:
        input_text = f"Caption: {caption}\nOCR Text: {ocr_text}\nIs this image related to horse racing? Yes or No."
        inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True)
        outputs = model.generate(inputs["input_ids"], max_length=50, pad_token_id=tokenizer.pad_token_id)
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return "yes" in response.lower()
    except Exception as e:
        print(f"Error with GPT classification: {e}")
        return False

# Classify and process images
def classify_image(processor, blip_model, image_path, ads_folder, gpt_model, gpt_tokenizer, csv_file):
    filename = os.path.basename(image_path)
    caption = generate_caption(processor, blip_model, image_path)
    ocr_text = sanitize_text(extract_ocr_text(image_path))
    if caption:
        print(f"Processing {filename}...\nCaption: {caption}\nOCR: {ocr_text}")
        is_related = is_related_to_horse_racing(caption, ocr_text, gpt_model, gpt_tokenizer)
        classification = "Yes" if is_related else "No"
        print(f"Classification: {classification}")
        if classification == "No":
            shutil.move(image_path, os.path.join(ads_folder, filename))
        save_to_csv(filename, caption, ocr_text, classification, csv_file)

# Save data to CSV
def save_to_csv(image_name, caption, ocr_text, classification, csv_file):
    with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([image_name, caption, ocr_text, classification])

# Main function
def main(input_folder, csv_file):
    ads_folder = os.path.join(input_folder, "ads")
    os.makedirs(ads_folder, exist_ok=True)
    processor, blip_model = initialize_blip_model()
    gpt_model, gpt_tokenizer = initialize_gpt_model()

    # Initialize CSV
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Image", "Caption", "OCR Text", "Classification"])

    # Process images
    for filename in os.listdir(input_folder):
        file_path = os.path.join(input_folder, filename)
        if os.path.isfile(file_path):
            classify_image(processor, blip_model, file_path, ads_folder, gpt_model, gpt_tokenizer, csv_file)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <path_to_images_folder>")
        sys.exit(1)

    input_folder = sys.argv[1]
    if not os.path.isdir(input_folder):
        print(f"Error: Folder '{input_folder}' does not exist or is not a directory.")
        sys.exit(1)

    main(input_folder, "image_data.csv")
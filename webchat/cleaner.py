import os
import re

# Folder containing the scraped text files
TEXT_FOLDER = "scraped_texts"
CLEANED_FOLDER = "cleaned_texts"

# Create folder for cleaned text files
if not os.path.exists(CLEANED_FOLDER):
    os.mkdir(CLEANED_FOLDER)

# Function to clean extracted text
def clean_text(text):
    # Remove multiple spaces, newlines, and extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove unnecessary characters (optional: e.g., special symbols)
    text = re.sub(r'[^\w\s.,;!?€$€]', '', text)

    # Remove very short lines (likely menu items or junk)
    lines = [line.strip() for line in text.split('.') if len(line.strip()) > 20]
    
    return '. '.join(lines)

# Process all text files
for file_name in os.listdir(TEXT_FOLDER):
    if file_name.endswith(".txt"):
        file_path = os.path.join(TEXT_FOLDER, file_name)
        
        # Read the raw text
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        # Clean the text
        cleaned_text = clean_text(raw_text)

        # Save cleaned text
        cleaned_file_path = os.path.join(CLEANED_FOLDER, file_name)
        with open(cleaned_file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)

print("Cleaning complete. Files saved in 'cleaned_texts'.")

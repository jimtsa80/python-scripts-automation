from transformers import BertTokenizer, TFBertModel
import os
import faiss
import numpy as np

# Paths
TEXT_FOLDER = r"C:\\Users\\jimtsa\\Desktop\\python-scripts-automation\\webchat\\cleaned_texts"
INDEX_FILE = "faiss_index.bin"

# Load pre-trained BERT tokenizer and model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = TFBertModel.from_pretrained('bert-base-uncased')

# Function to preprocess text and get embeddings
def get_text_embeddings(texts):
    # Tokenize the text
    encodings = tokenizer(texts, padding=True, truncation=True, return_tensors='tf')
    # Get the BERT model output (use the pooled_output for sentence embedding)
    outputs = model(encodings)
    sentence_embeddings = outputs.pooler_output
    return sentence_embeddings.numpy()

# Read all text files and create embeddings
texts = []
file_names = []
for file in os.listdir(TEXT_FOLDER):
    if file.endswith(".txt"):
        with open(os.path.join(TEXT_FOLDER, file), "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                texts.append(content)
                file_names.append(file)

# Convert texts to embeddings using BERT model
text_embeddings = get_text_embeddings(texts)

# Create and save FAISS index
index = faiss.IndexFlatL2(text_embeddings.shape[1])  # L2 distance index
index.add(text_embeddings)
faiss.write_index(index, INDEX_FILE)

# Save text mappings
with open("index_mappings.txt", "w", encoding="utf-8") as f:
    for i, file_name in enumerate(file_names):
        f.write(f"{i}\t{file_name}\n")

print(f"Indexed {len(texts)} documents. Index saved to {INDEX_FILE}")

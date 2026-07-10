import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from transformers import pipeline

# Path to your documents and the FAISS index file
DOCUMENTS_PATH = r"C:\Users\jimtsa\Desktop\python-scripts-automation\webchat\cleaned_texts"
INDEX_FILE = "faiss_index.bin"

# Initialize SentenceTransformer model (replace with your model)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize Hugging Face Question-Answering pipeline
qa_pipeline = pipeline("question-answering", model="deepset/roberta-base-squad2")

# Read documents and create embeddings
documents = []
file_names = []
for file in os.listdir(DOCUMENTS_PATH):
    if file.endswith(".txt"):
        with open(os.path.join(DOCUMENTS_PATH, file), "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                documents.append(content)
                file_names.append(file)

# Convert documents to embeddings
embeddings = model.encode(documents, convert_to_numpy=True)

# Create and save FAISS index
index = faiss.IndexFlatL2(embeddings.shape[1])  # L2 distance index
index.add(embeddings)
faiss.write_index(index, INDEX_FILE)

# Save mappings between indices and document names for later use
with open("index_mappings.txt", "w", encoding="utf-8") as f:
    for i, file_name in enumerate(file_names):
        f.write(f"{i}\t{file_name}\n")

print(f"Indexed {len(documents)} documents. Index saved to {INDEX_FILE}")

# Function to get the embedding for a query
def get_query_embedding(query):
    query_embedding = model.encode([query], convert_to_numpy=True)
    return query_embedding

# Function to retrieve relevant context from the FAISS index
def retrieve_context(query, k=3):
    query_embedding = get_query_embedding(query)
    
    print(f"Query embedding shape: {query_embedding.shape}")
    
    # Perform the FAISS search
    _, indices = index.search(np.array(query_embedding).astype(np.float32), k)
    
    # Ensure that indices are within bounds
    if len(indices[0]) > 0:
        relevant_contexts = [documents[i] for i in indices[0]]
    else:
        relevant_contexts = []
        print("No relevant contexts found!")
    
    return relevant_contexts

# Function to answer the query based on the context retrieved
def answer_query(query, k=3):
    relevant_contexts = retrieve_context(query, k)
    if relevant_contexts:
        # Join the relevant contexts into one string
        context = " ".join(relevant_contexts)
        
        # Use the QA model to extract the answer from the context
        result = qa_pipeline(question=query, context=context)
        return result['answer']
    else:
        return "No relevant information found."

# Test with a query
query = "Ποιοι είναι οι στόχοι του baby bank"
answer = answer_query(query, k=3)
print("Answer:", answer)

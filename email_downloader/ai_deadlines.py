import requests
import json

def load_text(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def query_ollama(prompt, model="phi3:mini"):
    response = requests.post(
        "http://localhost:11434/api/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False
        })
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()

def extract_deadlines(text):
    prompt = (
        "You are a deadline extraction bot.\n"
        "Your job is to EXTRACT ONLY deadlines from the text provided.\n"
        "For each deadline, identify the project or task (if mentioned) and the deadline expression.\n"
        "Only output bullet points in the following format (no headers, no explanation, no summary, no other text):\n"
        "- [Project or Task] – [Deadline]\n\n"
        "If there are no deadlines, output ONLY: [NO DEADLINES FOUND]\n"
        "Do NOT summarize. Do NOT add any extra explanation.\n"
        f"Text:\n{text[:12000]}\n\n"
        "Respond ONLY with the bullet-point list as specified."
    
    )
    return query_ollama(prompt)

# === MAIN EXECUTION ===
text = load_text("emails_last_30_days.txt")
results = extract_deadlines(text)

with open("extracted_deadlines.txt", "w", encoding="utf-8") as f:
    f.write(results)

print("✅ Deadlines written to extracted_deadlines.txt")
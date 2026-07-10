import spacy
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from scipy.special import softmax

INPUT_FILE = "transcripts/audio12/full_transcript.txt"
OUTPUT_XLSX = "ao_sentiment.xlsx"

# AO evaluation function
def is_ao_evaluated(sentence):
    sentence_lower = sentence.lower()
    ao_keywords = [
        " ao ", "the ao", "australian open", "the australian open", 
        "australian open media", " ao media",
        "australian open organization", "australian open management", " ao management", 
        "aus open", "ausopen", "tennis australia"
    ]
    return any(pattern in sentence_lower for pattern in ao_keywords)

print("Loading spaCy...")
nlp = spacy.load("en_core_web_sm")

print("Loading sentiment model...")
MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL)

def hf_sentiment(sentence):
    inputs = tokenizer(sentence, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
        scores = outputs.logits[0].numpy()
        probs = softmax(scores)
        labels = ["negative", "neutral", "positive"]
        max_idx = probs.argmax()
        return labels[max_idx], float(probs[max_idx]), dict(zip(labels, map(float, probs)))

print("Reading transcript...", flush=True)
records = []
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            speaker, text = line.split(":", 1)
            speaker = speaker.strip()
            text = text.strip()
        else:
            speaker = ""
            text = line.strip()
        for sent in nlp(text).sents:
            sent_text = sent.text.strip()
            if sent_text:
                records.append({
                    "speaker": speaker,
                    "sentence": sent_text
                })
print(f"Total sentences: {len(records)}")

filtered_records = []
for i, rec in enumerate(records, 1):
    sent = rec["sentence"]
    if is_ao_evaluated(sent):
        label, confidence, all_probs = hf_sentiment(sent)
        sentiment_score = all_probs["positive"] - all_probs["negative"] # -1 to +1
        rec["sentiment"] = label
        rec["confidence"] = confidence
        rec["sentiment_score"] = sentiment_score
        rec["proba_negative"] = all_probs["negative"]
        rec["proba_neutral"] = all_probs["neutral"]
        rec["proba_positive"] = all_probs["positive"]
        filtered_records.append(rec)
        if i % 5 == 0:
            print(f"Processed {i} AO sentences...", end='\r')

print(f"AO organization-evaluated sentences: {len(filtered_records)}")
if not filtered_records:
    print("No AO-evaluated sentences found!")
    exit()

cols = ["speaker", "sentence", "sentiment", "confidence", "sentiment_score", "proba_negative", "proba_neutral", "proba_positive"]
df = pd.DataFrame(filtered_records, columns=cols)
excel_writer = pd.ExcelWriter(OUTPUT_XLSX, engine='openpyxl')
df.to_excel(excel_writer, index=False, sheet_name="Sentiment Analysis")
ws = excel_writer.sheets["Sentiment Analysis"]

# Style header and cells
header_fill = PatternFill(start_color="1F4E78", fill_type="solid")
header_font = Font(bold=True, color="FFFFFF")
header_align = Alignment(horizontal="center", vertical="center")
for col in range(1, len(cols) + 1):
    cell = ws.cell(row=1, column=col)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = header_align
    ws.column_dimensions[get_column_letter(col)].width = max(17, len(cell.value)+2)

sentiment_colors = {
    "negative": "FFC7CE", "neutral": "FFEB9C", "positive": "C6EFCE"
}
for row in range(2, ws.max_row + 1):
    label = ws.cell(row=row, column=cols.index("sentiment")+1).value
    color = sentiment_colors.get(label, "FFFFFF")
    ws.cell(row=row, column=cols.index("sentiment")+1).fill = PatternFill(start_color=color, fill_type="solid")
    ws.cell(row=row, column=cols.index("sentiment")+1).alignment = Alignment(horizontal="center")
    ws.cell(row=row, column=cols.index("confidence")+1).number_format = "0.000"
    ws.cell(row=row, column=cols.index("sentiment_score")+1).number_format = "0.000"
    for c in ["proba_negative", "proba_neutral", "proba_positive"]:
        ws.cell(row=row, column=cols.index(c)+1).number_format = "0.000"

for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(cols)):
    for cell in row:
        cell.font = Font(name='Calibri', size=11)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
excel_writer.close()
print(f"\n✅ Excel file saved: {OUTPUT_XLSX}")
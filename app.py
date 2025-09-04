import streamlit as st
import pdfplumber
import docx
import pandas as pd
import re
from transformers import pipeline

# Load Hugging Face NER model
ner = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

# ---------------- File Reading Functions ----------------
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# ---------------- Regex Helpers ----------------
def extract_dates(text):
    # Matches formats like: 12 Jan 2025, January 12, 2025, 12/01/2025, 2025-01-12
    date_pattern = r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s\d{2,4}|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},\s\d{4})\b'
    return re.findall(date_pattern, text)

def extract_money(text):
    # Matches $100, ₹5000, USD 1,000, INR 200, etc.
    money_pattern = r'(\$?\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\s?(USD|INR|Rs|₹|\$)?)'
    return [m[0] for m in re.findall(money_pattern, text)]

# ---------------- Entity Extraction ----------------
def extract_entities(text):
    entities = ner(text[:2000])  # limit for speed
    clausewise = {
        "Parties": [],
        "Locations": [],
        "Agreement Type": [],
        "Clauses": [],
        "Dates": [],
        "Monetary Amounts": [],
        "Other": []
    }

    for ent in entities:
        etype = ent["entity_group"]
        word = ent["word"]

        if etype == "ORG":
            clausewise["Parties"].append(word)
            if "agreement" in word.lower() or "contract" in word.lower():
                clausewise["Agreement Type"].append(word)

        elif etype == "LOC":
            clausewise["Locations"].append(word)

        elif etype == "MISC":
            if "clause" in word.lower():
                clausewise["Clauses"].append(word)
            elif "agreement" in word.lower() or "contract" in word.lower():
                clausewise["Agreement Type"].append(word)
            else:
                clausewise["Other"].append(word)
        else:
            clausewise["Other"].append(word)

    # Add Dates & Money via regex
    clausewise["Dates"] = extract_dates(text)
    clausewise["Monetary Amounts"] = extract_money(text)

    # Remove duplicates
    for k in clausewise:
        clausewise[k] = list(set(clausewise[k]))

    return clausewise

# ---------------- Streamlit UI ----------------
st.title("📑 ClauseWise NER")
st.write("Upload a contract or paste text to extract Parties, Locations, Agreement Types, Clauses, Dates, and Monetary Amounts.")

# Text input
user_text = st.text_area("✍ Paste Contract Text:")

# File upload
uploaded_file = st.file_uploader("📂 Upload PDF or DOCX", type=["pdf", "docx"])

text = ""
if user_text:
    text = user_text
elif uploaded_file:
    if uploaded_file.name.endswith(".pdf"):
        text = read_pdf(uploaded_file)
    elif uploaded_file.name.endswith(".docx"):
        text = read_docx(uploaded_file)

if text:
    st.subheader("🔍 ClauseWise Extracted Entities")
    results = extract_entities(text)

    for category, items in results.items():
        if items:
            st.markdown(f"{category}:")
            for item in items:
                st.write(f"- {item}")       
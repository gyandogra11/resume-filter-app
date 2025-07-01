# streamlit_app.py

import os
import re
import pytesseract
import shutil
import csv
from datetime import datetime
from pdf2image import convert_from_path
from PIL import Image
import streamlit as st
from openpyxl import Workbook

# Tesseract path
pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Folder setup
resume_folder = "resumes"
output_folder = "selected"
os.makedirs(resume_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# Experience extractor
def extract_experience(text):
    text_lower = text.lower()
    experience_years = 0

    numeric = re.findall(r'(\d+(?:\.\d+)?)\s*(\+)?\s*(years?|yrs?)', text_lower)
    for match in numeric:
        try:
            experience_years = max(experience_years, float(match[0]))
        except:
            continue

    words_to_numbers = {
        'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
        'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
        'nineteen': 19, 'twenty': 20
    }
    for word, val in words_to_numbers.items():
        if re.search(rf"\\b{word}\\b\\s*(plus)?\\s*(years?|yrs?)", text_lower):
            experience_years = max(experience_years, val)

    parens = re.findall(r'\((\d{1,2})\)', text_lower)
    for p in parens:
        try:
            val = int(p)
            if val >= 5:
                experience_years = max(experience_years, val)
        except:
            continue

    for word, val in words_to_numbers.items():
        if f"over {word}" in text_lower or f"more than {word}" in text_lower:
            experience_years = max(experience_years, val)

    return experience_years

# Text from PDF
def extract_text_from_pdf(pdf_path):
    try:
        images = convert_from_path(pdf_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        return text
    except Exception as e:
        return ""

# Resume matching
def analyze_resume(text, filters):
    text_lower = text.lower()

    skills_found = [s for s in filters['skills'] if s in text_lower]
    has_required_skills = (len(skills_found) >= len(filters['skills']) if filters['match_all'] else len(skills_found) > 0)

    exp = extract_experience(text)
    has_enough_exp = exp >= filters['min_exp']

    qual = filters['qualification']
    is_undergrad = any(k in text_lower for k in ['b.tech', 'b.e', 'bachelor'])
    is_postgrad = any(k in text_lower for k in ['m.tech', 'mba', 'msc', 'master'])
    qual_match = qual == 'all' or (qual == 'undergraduate' and is_undergrad) or (qual == 'postgraduate' and is_postgrad)

    loc_match = filters['location'] == 'all' or filters['location'] in text_lower
    spec_match = any(s in text_lower for s in filters['specialization'].split())
    cert_match = True if not filters['certifications'] else any(c in text_lower for c in filters['certifications'])
    comp_match = filters['company'] == 'all' or filters['company'] in text_lower

    match = all([has_required_skills, has_enough_exp, qual_match, loc_match, spec_match, cert_match, comp_match])

    return match, exp, skills_found

# Streamlit UI
st.title("Resume Filter App")
st.markdown("Upload resumes in the 'resumes/' folder and click Filter.")

with st.form("filter_form"):
    skills = st.text_input("Required Skills (comma-separated)").lower().split(',')
    match_all = st.checkbox("Should ALL skills match?", value=False)
    min_exp = st.number_input("Minimum Experience (Years)", min_value=0.0, value=0.0)
    qualification = st.selectbox("Qualification", ["all", "undergraduate", "postgraduate"])
    location = st.text_input("Preferred Location (or 'all')", value="all").lower()
    specialization = st.text_input("Specialization", value="").lower()
    certifications = st.text_input("Certifications (comma-separated, optional)").lower().split(',')
    company = st.text_input("Last Working Company (or 'all')", value="all").lower()
    submit = st.form_submit_button("Filter Resumes")

if submit:
    st.info("Processing resumes...")

    filters = {
        'skills': [s.strip() for s in skills if s.strip()],
        'match_all': match_all,
        'min_exp': min_exp,
        'qualification': qualification,
        'location': location,
        'specialization': specialization,
        'certifications': [c.strip() for c in certifications if c.strip()],
        'company': company
    }

    matched = []
    for file in os.listdir(resume_folder):
        if file.lower().endswith(".pdf"):
            path = os.path.join(resume_folder, file)
            text = extract_text_from_pdf(path)
            is_match, experience, skills_found = analyze_resume(text, filters)

            if is_match:
                shutil.copy(path, os.path.join(output_folder, file))
                matched.append({
                    'Filename': file,
                    'Experience': experience,
                    'Skills': ", ".join(skills_found)
                })

    if matched:
        st.success(f"{len(matched)} resumes matched your criteria.")
        st.dataframe(matched)
    else:
        st.warning("No matching resumes found.")

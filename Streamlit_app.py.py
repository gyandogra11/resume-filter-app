import streamlit as st
import pandas as pd
import os
import re
import pytesseract
import shutil
from datetime import datetime
from pdf2image import convert_from_path
from PIL import Image

# Streamlit page settings
st.set_page_config(page_title="Resume Filter - Medhaj Techno Concepts Pvt. Ltd", layout="wide")

# App title and subtitle
st.title("Resume Filtering Dashboard – Medhaj Techno Concepts Pvt. Ltd")
st.markdown("Upload and filter resumes based on your criteria.")
st.markdown("---")

# Custom green button styling
st.markdown("""
    <style>
        div.stButton > button {
            background-color: #28a745;
            color: white;
            font-weight: bold;
            padding: 0.5em 1.5em;
            border: none;
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# Ensure folders exist
resume_folder = "resumes"
output_folder = "selected"
os.makedirs(resume_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# Input filters (one below the other)
skills_input = st.text_input("Required Skills (comma separated)").lower().split(',')
min_experience = st.number_input("Minimum Experience (years)", min_value=0.0, step=0.5)
qualification_input = st.selectbox("Qualification", ["All", "Undergraduate", "Postgraduate"]).lower()
location_input = st.text_input("Preferred Location (optional)").strip().lower()
specialization_input = st.text_input("Specialization (e.g. civil, electrical)").strip().lower()
certifications_input = st.text_input("Certifications (comma separated, optional)").lower().split(',')
certifications_input = [c.strip() for c in certifications_input if c.strip()]
company_input = st.text_input("Last Working Company (optional)").strip().lower()
match_all_skills = st.checkbox("Require all listed skills to match", value=True)

start = st.button("Start Filtering")

# Regex patterns
email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
phone_pattern = r'(\+91[\-\s]?)?[789]\d{9}|\(?\d{3,4}\)?[\s\-]?\d{6,8}'
experience_pattern = r'(\d+(?:\.\d+)?|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fifteen|twenty|thirty))\s*(years?|yrs?)'

# ✅ Your Poppler path — required for reading PDFs with pdf2image
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

# Extract text from a PDF using OCR
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
        for image in images:
            text += pytesseract.image_to_string(image)
    except Exception as e:
        st.error(f"Error reading {os.path.basename(pdf_path)}: {e}")
    return text.lower()

# Analyze resume content against the filters
def analyze_resume(text):
    email = re.search(email_pattern, text)
    phone = re.search(phone_pattern, text)
    experience_matches = re.findall(experience_pattern, text)

    # Calculate years of experience (supports words like "ten" or numbers)
    experience_years = 0
    for e in experience_matches:
        try:
            experience_years = max(experience_years, float(e[0]))
        except:
            word_to_num = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                'eleven': 11, 'twelve': 12, 'thirteen': 13,
                'fifteen': 15, 'twenty': 20, 'thirty': 30
            }
            word = e[0].lower()
            if word in word_to_num:
                experience_years = max(experience_years, word_to_num[word])

    # Skills matching (all or any)
    skill_match = all(skill.strip() in text for skill in skills_input if skill.strip()) if match_all_skills else any(skill.strip() in text for skill in skills_input if skill.strip())

    # Qualification matching
    undergrad = any(k in text for k in ['b.tech', 'btech', 'b.e', 'be', 'bachelor'])
    postgrad = any(k in text for k in ['m.tech', 'mtech', 'm.e', 'me', 'mba', 'msc', 'm.sc', 'master'])
    matches_qualification = (
        qualification_input == 'all' or
        (qualification_input == 'undergraduate' and undergrad) or
        (qualification_input == 'postgraduate' and postgrad)
    )

    # Other filter matches
    matches_location = location_input in text if location_input else True
    matches_specialization = specialization_input in text if specialization_input else True
    matches_certification = any(cert in text for cert in certifications_input) if certifications_input else True
    matches_company = company_input in text if company_input else True

    return {
        "email": email.group(0) if email else "Not found",
        "phone": phone.group(0) if phone else "Not found",
        "experience": experience_years,
        "matches": all([
            experience_years >= min_experience,
            skill_match,
            matches_qualification,
            matches_location,
            matches_specialization,
            matches_certification,
            matches_company
        ])
    }

# Resume filtering process
if start:
    st.info("Processing resumes...")
    csv_rows = []
    csv_header = ["Filename", "Email", "Phone", "Experience (yrs)"]

    for filename in os.listdir(resume_folder):
        if filename.lower().endswith(".pdf"):
            path = os.path.join(resume_folder, filename)
            raw_text = extract_text_from_pdf(path)
            result = analyze_resume(raw_text)

            if result["matches"]:
                shutil.copy(path, output_folder)
                csv_rows.append([
                    filename,
                    result["email"],
                    result["phone"],
                    result["experience"]
                ])

    if csv_rows:
        df = pd.DataFrame(csv_rows, columns=csv_header)
        st.success(f"{len(csv_rows)} resumes matched and saved in 'selected/' folder.")
        st.dataframe(df, use_container_width=True)
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv_data, file_name="filtered_candidates.csv", mime="text/csv")
    else:
        st.warning("No resumes matched the given criteria.")

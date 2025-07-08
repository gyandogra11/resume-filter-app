import os
import re
import shutil
import pytesseract
import pandas as pd
from datetime import datetime
from pdf2image import convert_from_path
from PIL import Image
import streamlit as st

# Fix for Poppler on Windows
os.environ["PATH"] += os.pathsep + r"C:\poppler-24.08.0\Library\bin"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Folder setup
resume_folder = "resumes"
output_folder = "selected"
os.makedirs(resume_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# File name for report
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
excel_file = f"filtered_candidates_{timestamp}.xlsx"

# App config
st.set_page_config(page_title="Resume Filter | Medhaj Tech", layout="centered")

# Title
st.markdown(
    "<h1 style='text-align: center; color: black;'>Resume Filtering Dashboard – Medhaj Techno Concepts Pvt. Ltd</h1>",
    unsafe_allow_html=True
)
st.markdown("<p style='text-align: center;'>Upload and filter resumes based on your criteria.</p>", unsafe_allow_html=True)
st.markdown("---")

# Input Fields with unique keys
skills_input = st.text_input("Required Skills (comma separated)", key="skills").lower().split(',')
skills_input = [skill.strip() for skill in skills_input if skill.strip()]

location_input = st.text_input("Preferred Location (optional)", key="location").strip().lower()

min_experience = st.number_input("Minimum Experience (years)", min_value=0.0, value=0.0, key="exp")

certifications_input = st.text_input("Certifications (comma separated, optional)", key="certs").lower().split(',')
certifications_input = [cert.strip() for cert in certifications_input if cert.strip()]

qualification_input = st.selectbox("Qualification", ["All", "Undergraduate", "Postgraduate"], key="qual").lower()

company_input = st.text_input("Last Working Company (optional)", key="company").strip().lower()

specialization_input = st.text_input("Specialization (e.g. civil, electrical)", key="spec").strip().lower()

match_all_skills = st.checkbox("Require all listed skills to match", value=True, key="matchskills")

# Start filtering
if st.button("Start Filtering", type="primary"):
    st.info("Processing resumes...")
    matched = []

    def extract_text_from_pdf(pdf_path):
        try:
            images = convert_from_path(pdf_path)
            text = ""
            for image in images:
                text += pytesseract.image_to_string(image)
            return text
        except Exception as e:
            st.error(f"Error reading {os.path.basename(pdf_path)}: {e}")
            return ""

    def analyze_resume(text):
        text = text.lower()
        email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        phone = re.search(r'(\+91[\-\s]?)?[789]\d{9}|\(?\d{3,4}\)?[\s\-]?\d{6,8}', text)
        experience_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', text)
        experience_years = max([float(e[0]) for e in experience_matches], default=0)

        skills_found = [skill for skill in skills_input if skill in text]
        skills_match = all(skill in text for skill in skills_input) if match_all_skills else bool(skills_found)

        undergrad = any(k in text for k in ['b.tech', 'btech', 'b.e', 'be', 'bachelor'])
        postgrad = any(k in text for k in ['m.tech', 'mtech', 'm.e', 'me', 'mba', 'msc', 'm.sc', 'master'])
        qualification_match = (
            qualification_input == "all" or
            (qualification_input == "undergraduate" and undergrad) or
            (qualification_input == "postgraduate" and postgrad)
        )

        location_match = location_input in text if location_input else True
        specialization_match = specialization_input in text if specialization_input else True
        certification_match = any(cert in text for cert in certifications_input) if certifications_input else True
        company_match = company_input in text if company_input else True

        overall_match = all([
            experience_years >= min_experience,
            skills_match,
            qualification_match,
            location_match,
            specialization_match,
            certification_match,
            company_match
        ])

        return {
            "email": email.group(0) if email else "Not found",
            "phone": phone.group(0) if phone else "Not found",
            "experience": experience_years,
            "skills": skills_found,
            "match": overall_match
        }

    for file in os.listdir(resume_folder):
        if file.lower().endswith(".pdf"):
            path = os.path.join(resume_folder, file)
            text = extract_text_from_pdf(path)
            result = analyze_resume(text)

            if result['match']:
                shutil.copy(path, os.path.join(output_folder, file))
                matched.append({
                    "Filename": file,
                    "Email": result["email"],
                    "Phone": result["phone"],
                    "Experience (yrs)": result["experience"],
                    "Skills Found": ", ".join(result["skills"])
                })

    if matched:
        st.success(f"{len(matched)} resumes matched your criteria.")
        df = pd.DataFrame(matched)
        st.dataframe(df)
        df.to_excel(excel_file, index=False)
        with open(excel_file, "rb") as f:
            st.download_button("Download Excel Report", f, file_name=excel_file)
    else:
        st.warning("No matching resumes found.")

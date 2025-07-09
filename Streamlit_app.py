import os
import re
import fitz
import shutil
import calendar
import streamlit as st
import pandas as pd
from datetime import datetime
from docx import Document
from openpyxl import Workbook

# Ensure required folders exist
os.makedirs("resumes", exist_ok=True)
os.makedirs("selected", exist_ok=True)

st.set_page_config(page_title="Resume Filter | Medhaj", layout="centered")

st.markdown("""
    <h1 style='text-align: center;'>Resume Filtering Dashboard – Medhaj Techno Concepts Pvt. Ltd</h1>
    <p style='text-align: center;'>Upload and filter resumes based on your criteria.</p>
    <hr>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader("Upload Resumes (PDF or Word)", type=["pdf", "docx"], accept_multiple_files=True)

qualification_input = st.selectbox("Qualification", ["All", "Undergraduate", "Postgraduate"]).lower()
skills_input = st.text_input("Required Qualifications/Skills (e.g. b.e, b.tech, m.tech, etc) *comma separated").lower().split(',')
skills_input = [s.strip() for s in skills_input if s.strip()]
min_experience = st.number_input("Minimum Experience (years)", min_value=0.0, step=0.5)
location_input = st.text_input("Preferred Location (e.g. Delhi, Mumbai or all)").strip().lower()
specialization_input = st.text_input("Specialization (e.g. civil, electrical)").strip().lower()
certifications_input = st.text_input("Certifications (comma separated, optional)").lower().split(',')
certifications_input = [c.strip() for c in certifications_input if c.strip()]
company_input = st.text_input("Last Working Company (optional)").strip().lower()
match_all_skills = st.checkbox("Require all listed skills to match", value=True)

def extract_text(file):
    if file.name.lower().endswith(".pdf"):
        try:
            with fitz.open(stream=file.read(), filetype="pdf") as doc:
                return "\n".join(page.get_text() for page in doc)
        except Exception as e:
            st.error(f"PDF error in {file.name}: {e}")
    elif file.name.lower().endswith(".docx"):
        try:
            doc = Document(file)
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except Exception as e:
            st.error(f"DOCX error in {file.name}: {e}")
    return ""

def calculate_experience_from_range(text):
    months = {month.lower(): index for index, month in enumerate(calendar.month_name) if month}
    month_regex = re.compile(
        r'(?P<start_month>\b\w+\b)\s*(?P<start_year>\d{4})\s*[-to–]+\s*(?P<end_month>\b\w+\b)\s*(?P<end_year>\d{4})',
        re.IGNORECASE
    )
    total_months = 0
    for match in month_regex.finditer(text):
        try:
            sm = months[match.group("start_month").lower()]
            sy = int(match.group("start_year"))
            em = months[match.group("end_month").lower()]
            ey = int(match.group("end_year"))
            delta_months = (ey - sy) * 12 + (em - sm)
            if delta_months > 0:
                total_months += delta_months
        except:
            continue
    return round(total_months / 12, 2)

def analyze_resume(text):
    text_lower = text.lower()
    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    phone = re.search(r'(\+91[\-\s]?)?[789]\d{9}|\(?\d{3,4}\)?[\s\-]?\d{6,8}', text)

    numeric_exp = re.findall(r'(\d+(?:\.\d+)?)\s*(years?|yrs?)', text_lower)
    numeric_exp_years = max([float(e[0]) for e in numeric_exp], default=0.0)
    month_range_exp = calculate_experience_from_range(text)
    experience_years = round(max(numeric_exp_years, month_range_exp), 2)

    skills_found = [s for s in skills_input if s in text_lower]
    skills_match = all(s in text_lower for s in skills_input) if match_all_skills else any(s in text_lower for s in skills_input)

    undergrad_keywords = ['b.tech', 'btech', 'b.e', 'be', 'bachelor']
    postgrad_keywords = ['m.tech', 'mtech', 'm.e', 'me', 'mba', 'msc', 'm.sc', 'master']
    is_undergrad = any(k in text_lower for k in undergrad_keywords)
    is_postgrad = any(k in text_lower for k in postgrad_keywords)
    qual_match = (
        qualification_input == "all" or
        (qualification_input == "undergraduate" and is_undergrad) or
        (qualification_input == "postgraduate" and is_postgrad)
    )

    location_match = location_input in text_lower if location_input else True
    specialization_match = specialization_input in text_lower if specialization_input else True
    cert_match = any(cert in text_lower for cert in certifications_input) if certifications_input else True
    company_match = company_input in text_lower if company_input else True
    experience_match = experience_years >= min_experience

    is_match = all([
        skills_match, qual_match, location_match,
        specialization_match, cert_match, company_match, experience_match
    ])

    return {
        "email": email.group(0) if email else "Not found",
        "phone": phone.group(0) if phone else "Not found",
        "experience": experience_years,
        "skills_found": skills_found,
        "match": is_match
    }

if st.button("Start Filtering"):
    if not uploaded_files:
        st.warning("Please upload resumes to begin.")
    else:
        results = []
        for file in uploaded_files:
            text = extract_text(file)
            analysis = analyze_resume(text)
            if analysis["match"]:
                with open(os.path.join("resumes", file.name), "wb") as f:
                    f.write(file.getbuffer())
                shutil.copy(os.path.join("resumes", file.name), os.path.join("selected", file.name))
                results.append({
                    "Filename": file.name,
                    "Email": analysis["email"],
                    "Phone": analysis["phone"],
                    "Experience (yrs)": analysis["experience"],
                    "Skills Found": ", ".join(analysis["skills_found"])
                })

        if results:
            st.success(f"{len(results)} resumes matched your criteria.")
            df = pd.DataFrame(results)
            st.dataframe(df)
            filename = f"filtered_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.append(["Filename", "Email", "Phone", "Experience (yrs)", "Skills Found"])
            for row in results:
                ws.append([row["Filename"], row["Email"], row["Phone"], row["Experience (yrs)"], row["Skills Found"]])
            wb.save(filename)
            with open(filename, "rb") as f:
                st.download_button("Download Excel Report", f, file_name=filename)
        else:
            st.warning("No resumes matched your criteria.")
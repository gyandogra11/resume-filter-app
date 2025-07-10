import os
import re
import fitz
import shutil
import zipfile
import calendar
import streamlit as st
import pandas as pd
import docx2txt
from datetime import datetime
from openpyxl import Workbook

os.makedirs("resumes", exist_ok=True)
os.makedirs("selected", exist_ok=True)

st.set_page_config(page_title="Resume Filter | Medhaj", layout="centered")

st.markdown("""
    <h1 style='text-align: center;'>Resume Filtering Dashboard – Medhaj Techno Concepts Pvt. Ltd</h1>
    <p style='text-align: center;'>Upload and filter resumes based on your criteria.</p>
    <hr>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader("Upload Resumes (PDF or DOC/DOCX)", type=["pdf", "doc", "docx"], accept_multiple_files=True)

qualification_input = st.selectbox("Qualification", ["All", "Undergraduate", "Postgraduate"]).lower()

skills_input = st.text_input("Required Qualifications/Skills (e.g. b.e, diploma, etc) *comma separated").lower().split(',')
skills_input = [s.strip() for s in skills_input if s.strip()]

min_experience = st.number_input("Minimum Experience (years)", min_value=0.0, step=0.5)

location_input = st.text_input("Preferred Location (e.g. Delhi, Mumbai or all)").strip().lower()
specialization_input = st.text_input("Specialization (e.g. civil, mechanical, electrical)").strip().lower()

certifications_input = st.text_input("Certifications (comma separated, optional)").lower().split(',')
certifications_input = [c.strip() for c in certifications_input if c.strip()]

company_input = st.text_input("Last Working Company (optional)").strip().lower()
match_all_skills = st.checkbox("Require all listed skills to match", value=True)

def extract_text(file):
    try:
        if file.name.endswith(".pdf"):
            with fitz.open(stream=file.read(), filetype="pdf") as doc:
                return "\n".join([page.get_text() for page in doc])
        elif file.name.endswith((".doc", ".docx")):
            return docx2txt.process(file)
    except Exception as e:
        st.error(f"Error reading {file.name}: {e}")
    return ""

def calculate_experience_from_range(text):
    months = {month.lower(): index for index, month in enumerate(calendar.month_name) if month}
    month_regex = re.compile(r'(?P<start_month>\b\w+\b)\s*(?P<start_year>\d{4})\s*[-to–]+\s*(?P<end_month>\b\w+\b)\s*(?P<end_year>\d{4})', re.IGNORECASE)
    total_months = 0
    for match in month_regex.finditer(text):
        try:
            sm, sy = months[match.group("start_month").lower()], int(match.group("start_year"))
            em, ey = months[match.group("end_month").lower()], int(match.group("end_year"))
            start_date, end_date = datetime(sy, sm, 1), datetime(ey, em, 1)
            if end_date >= start_date:
                total_months += (ey - sy) * 12 + (em - sm)
        except Exception:
            continue
    return round(total_months / 12, 2)

def analyze_resume(text):
    text_lower = text.lower()
    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    phone = re.search(r'(\+91[\-\s]?)?[789]\d{9}|\(?\d{3,4}\)?[\s\-]?\d{6,8}', text)
    numeric_exp = re.findall(r'(\d+(?:\.\d+)?)\s*(years?|yrs?)', text_lower)
    exp_years = max([float(e[0]) for e in numeric_exp], default=0.0)
    range_exp = calculate_experience_from_range(text)
    experience = round(max(exp_years, range_exp), 2)

    found_skills = [skill for skill in skills_input if skill in text_lower]
    skills_match = all(skill in text_lower for skill in skills_input) if match_all_skills else any(skill in text_lower for skill in skills_input)

    undergrad_keywords = ['b.tech', 'btech', 'b.e', 'be', 'bachelor', 'diploma', 'polytechnic']
    postgrad_keywords = ['m.tech', 'mtech', 'm.e', 'me', 'mba', 'msc', 'm.sc', 'master']
    is_undergrad = any(k in text_lower for k in undergrad_keywords)
    is_postgrad = any(k in text_lower for k in postgrad_keywords)

    qualification_match = qualification_input == "all" or \
        (qualification_input == "undergraduate" and is_undergrad) or \
        (qualification_input == "postgraduate" and is_postgrad)

    location_match = location_input in text_lower if location_input else True
    specialization_keywords = {
        'civil': ['civil', 'construction', 'structural', 'geotechnical', 'environmental'],
        'mechanical': ['mechanical', 'mechatronics', 'automobile', 'thermal', 'manufacturing'],
        'electrical': ['electrical', 'power systems', 'electronics', 'instrumentation', 'control systems']
    }
    specialization_match = any(kw in text_lower for kw in specialization_keywords.get(specialization_input, [])) if specialization_input else True

    cert_match = any(c in text_lower for c in certifications_input) if certifications_input else True
    company_match = company_input in text_lower if company_input else True
    experience_match = experience >= min_experience

    is_match = all([skills_match, qualification_match, location_match, specialization_match, cert_match, company_match, experience_match])

    return {
        "email": email.group(0) if email else "Not found",
        "phone": phone.group(0) if phone else "Not found",
        "experience": experience,
        "skills_found": found_skills,
        "match": is_match
    }

if st.button("Start Filtering"):
    if not uploaded_files:
        st.warning("Please upload at least one resume.")
    else:
        results = []
        for file in uploaded_files:
            text = extract_text(file)
            analysis = analyze_resume(text)
            if analysis["match"]:
                filepath = os.path.join("selected", file.name)
                with open(filepath, "wb") as f:
                    f.write(file.getbuffer())
                results.append({
                    "Filename": file.name,
                    "Email": analysis["email"],
                    "Phone": analysis["phone"],
                    "Experience (yrs)": analysis["experience"],
                    "Skills Found": ", ".join(analysis["skills_found"])
                })

        if results:
            df = pd.DataFrame(results)
            st.success(f"{len(results)} resumes matched your criteria.")
            st.dataframe(df)

            excel_file = f"filtered_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.append(["Filename", "Email", "Phone", "Experience (yrs)", "Skills Found"])
            for r in results:
                ws.append([r["Filename"], r["Email"], r["Phone"], r["Experience (yrs)"], r["Skills Found"]])
            wb.save(excel_file)

            with open(excel_file, "rb") as f:
                st.download_button("Download Excel Report", f, file_name=excel_file)

            zip_path = "selected_resumes.zip"
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for resume in os.listdir("selected"):
                    zipf.write(os.path.join("selected", resume), resume)
            with open(zip_path, "rb") as f:
                st.download_button("Download Matched Resumes ZIP", f, file_name=zip_path, mime="application/zip")
        else:
            st.warning("No resumes matched your criteria.")
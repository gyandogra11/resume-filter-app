import os
import re
import shutil
import fitz  # PyMuPDF
import streamlit as st
import pandas as pd
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

uploaded_files = st.file_uploader("Upload PDF Resumes", type="pdf", accept_multiple_files=True)

skills_input = st.text_input("Required Skills (comma separated)").lower().split(',')
skills_input = [s.strip() for s in skills_input if s.strip()]
min_experience = st.number_input("Minimum Experience (years)", min_value=0.0, step=0.5)
qualification_input = st.selectbox("Qualification", ["All", "Undergraduate", "Postgraduate"]).lower()
location_input = st.text_input("Preferred Location (optional)").strip().lower()
specialization_input = st.text_input("Specialization (e.g. civil, electrical)").strip().lower()
certifications_input = st.text_input("Certifications (comma separated, optional)").lower().split(',')
certifications_input = [c.strip() for c in certifications_input if c.strip()]
company_input = st.text_input("Last Working Company (optional)").strip().lower()
match_all_skills = st.checkbox("Require all listed skills to match", value=True)

def extract_text_from_pdf(file):
    try:
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            return "\n".join([page.get_text() for page in doc])
    except Exception as e:
        st.error(f"Error reading {file.name}: {e}")
        return ""

def analyze_resume(text):
    text_lower = text.lower()
    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    phone = re.search(r'(\+91[\-\s]?)?[789]\d{9}|\(?\d{3,4}\)?[\s\-]?\d{6,8}', text)
    experience_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(years?|yrs?)', text_lower)
    experience_years = max([float(e[0]) for e in experience_matches], default=0)

    skills_match = all(skill in text_lower for skill in skills_input) if match_all_skills else any(skill in text_lower for skill in skills_input)

    undergrad = any(k in text_lower for k in ['b.tech', 'btech', 'b.e', 'be', 'bachelor'])
    postgrad = any(k in text_lower for k in ['m.tech', 'mtech', 'm.e', 'me', 'mba', 'msc', 'm.sc', 'master'])
    qual_match = (
        qualification_input == "all" or
        (qualification_input == "undergraduate" and undergrad) or
        (qualification_input == "postgraduate" and postgrad)
    )

    return {
        "email": email.group(0) if email else "Not found",
        "phone": phone.group(0) if phone else "Not found",
        "experience": experience_years,
        "skills_found": [s for s in skills_input if s in text_lower],
        "match": all([
            skills_match,
            experience_years >= min_experience,
            qual_match,
            location_input in text_lower if location_input else True,
            specialization_input in text_lower if specialization_input else True,
            any(c in text_lower for c in certifications_input) if certifications_input else True,
            company_input in text_lower if company_input else True
        ])
    }

if st.button("Start Filtering"):
    if not uploaded_files:
        st.warning("Please upload at least one resume.")
    else:
        results = []
        for file in uploaded_files:
            text = extract_text_from_pdf(file)
            result = analyze_resume(text)
            if result["match"]:
                with open(os.path.join("resumes", file.name), "wb") as f:
                    f.write(file.getbuffer())
                shutil.copy(os.path.join("resumes", file.name), os.path.join("selected", file.name))
                results.append({
                    "Filename": file.name,
                    "Email": result["email"],
                    "Phone": result["phone"],
                    "Experience (yrs)": result["experience"],
                    "Skills Found": ", ".join(result["skills_found"])
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
            st.warning("No matching resumes found.")

import os
import re
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from fuzzywuzzy import fuzz
import gradio as gr
import tempfile
import shutil

# Master skill list
skill_list = [
    'python', 'machine learning', 'deep learning', 'sql', 'aws', 'numpy',
    'javascript', 'c++', 'c', 'html', 'css', 'nlp', 'react', 'java',
    'excel', 'pandas', 'tensorflow', 'web scraping', 'google colab'
]

# Degree list
degree_list = [
    'bachelor', 'b.tech', 'm.tech', 'msc', 'mba', 'bsc', 'phd', 'doctorate', 
    'master', "master's", "bachelor's", "int. msc", "b.sc", "m.sc"
]

def clean_text(text):
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_skills(text, skill_list, fuzzy=True, threshold=85):
    text = clean_text(text)
    skills_found = []

    for skill in skill_list:
        skill_pattern = re.escape(skill)
        if re.search(r'\b' + skill_pattern + r'\b', text):
            skills_found.append(skill)

    if fuzzy:
        for skill in skill_list:
            if skill not in skills_found:
                score = fuzz.partial_ratio(skill, text)
                if score >= threshold:
                    skills_found.append(skill)

    return list(set(skills_found))

def extract_experience(text):
    exp_pattern = r'(\d{1,2}\+?\s*(?:years|yrs|year))'
    matches = re.findall(exp_pattern, text.lower())
    return matches

def extract_degrees(text):
    found_degrees = []
    text = text.lower()
    for degree in degree_list:
        if re.search(r'\b' + re.escape(degree) + r'\b', text):
            found_degrees.append(degree)
    return list(set(found_degrees))

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ''
    return text

def process_resumes(jd_text, uploaded_resumes):
    required_skills = extract_skills(jd_text, skill_list)
    if not required_skills:
        return "❌ No skills detected in Job Description.", None

    all_results = []

    for resume_file in uploaded_resumes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(resume_file.read())
            tmp_path = tmp.name

        text = extract_text_from_pdf(tmp_path)
        skills = extract_skills(text, skill_list)
        experience = extract_experience(text)
        degrees = extract_degrees(text)

        matched_skills = [skill for skill in skills if skill in required_skills]
        skill_gaps = [skill for skill in required_skills if skill not in skills]

        match_percentage = round((len(matched_skills) / len(required_skills)) * 100, 2) if required_skills else 0

        all_results.append({
            'Resume': resume_file.name,
            'Match %': match_percentage,
            'Matched Skills': ", ".join(matched_skills),
            'Skill Gaps': ", ".join(skill_gaps),
            'Experience': ", ".join(experience),
            'Degrees': ", ".join(degrees),
        })

        os.remove(tmp_path)

    df = pd.DataFrame(all_results)
    df_sorted = df.sort_values(by='Match %', ascending=False).reset_index(drop=True)
    return df_sorted.to_markdown(index=False), df_sorted

def launch_app(jd_text, resumes):
    markdown_table, _ = process_resumes(jd_text, resumes)
    return markdown_table

# 🎯 Gradio UI
iface = gr.Interface(
    fn=launch_app,
    inputs=[
        gr.Textbox(label="Paste Job Description Here", lines=10),
        gr.File(label="Upload Resume PDFs", file_types=['.pdf'], file_count="multiple")
    ],
    outputs=gr.Markdown(label="📄 Ranked Resumes (Skill Match %)"),
    title="Resume Matcher",
    description="Upload multiple resumes and paste a Job Description. Get a ranked list based on skill match, degrees, and experience.",
)

iface.launch(server_name="0.0.0.0", server_port=10000)

      

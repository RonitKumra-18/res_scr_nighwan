import os
import re
import pdfplumber
import pandas as pd
import matplotlib.pyplot.pyplot as plt
import gradio as gr
from fuzzywuzzy import fuzz
from io import BytesIO

skill_list = ['python', 'machine learning', 'deep learning', 'sql', 'aws', 'numpy',
              'javascript', 'c++', 'c', 'html', 'css', 'nlp', 'react', 'java', 
              'excel', 'pandas', 'tensorflow', 'web scraping', 'google colab']

degree_list = ['bachelor', 'b.tech', 'm.tech', 'msc', 'mba', 'bsc', 'phd', 'doctorate', 
               'master',"master's","bachelor's", "int. msc","b.sc","m.sc"]

def clean_text(text):
    return re.sub(r'\s+', ' ', text.lower())

def extract_skills(text, skill_list, fuzzy=True, threshold=85):
    text = clean_text(text)
    skills_found = []

    for skill in skill_list:
        if re.search(r'\b' + re.escape(skill) + r'\b', text):
            skills_found.append(skill)

    if fuzzy:
        for skill in skill_list:
            if skill not in skills_found:
                score = fuzz.partial_ratio(skill, text)
                if score >= threshold:
                    skills_found.append(skill)

    return list(set(skills_found))

def extract_experience(text):
    return re.findall(r'(\d{1,2}\+?\s*(?:years|yrs|year))', text.lower())

def extract_degrees(text):
    return list(set([deg for deg in degree_list if re.search(r'\b' + re.escape(deg) + r'\b', text.lower())]))

def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(BytesIO(file.read())) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ''
    return text

def process_resumes(jd_input, resume_files):
    required_skills = extract_skills(jd_input, skill_list)
    results = []

    for resume_file in resume_files:
        resume_name = resume_file.name
        text = extract_text_from_pdf(resume_file)

        skills = extract_skills(text, skill_list)
        experience = extract_experience(text)
        degrees = extract_degrees(text)

        matched_skills = [s for s in skills if s in required_skills]
        skill_gaps = [s for s in required_skills if s not in skills]
        match_percent = round((len(matched_skills)/len(required_skills))*100, 2) if required_skills else 0

        results.append({
            'Resume': resume_name,
            'Match %': match_percent,
            'Matched Skills': ', '.join(matched_skills),
            'Skill Gaps': ', '.join(skill_gaps),
            'Experience': ', '.join(experience),
            'Degrees': ', '.join(degrees)
        })

    df = pd.DataFrame(results).sort_values(by='Match %', ascending=False).reset_index(drop=True)
    return df

def app(jd_input, resume_files):
    df = process_resumes(jd_input, resume_files)
    return gr.Dataframe.update(value=df)

gr.Interface(
    fn=app,
    inputs=[
        gr.Textbox(label="Paste Full Job Description"),
        gr.File(file_types=['.pdf'], file_count='multiple', label="Upload Resumes (PDFs only)")
    ],
    outputs=gr.Dataframe(label="Ranked Resumes")
).launch()

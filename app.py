import os
import re
import io
import shutil
import tempfile
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
from fuzzywuzzy import fuzz
import gradio as gr

# ---- Configurable Lists ----
skill_list = ['python', 'machine learning', 'deep learning', 'sql', 'aws', 'numpy',
              'javascript', 'c++', 'c', 'html', 'css', 'nlp', 'react', 'java',
              'excel', 'pandas', 'tensorflow', 'web scraping', 'google colab']

degree_list = ['bachelor', 'b.tech', 'm.tech', 'msc', 'mba', 'bsc', 'phd', 'doctorate',
               'master', "master's", "bachelor's", "int. msc", "b.sc", "m.sc"]

# ---- Utilities ----
def clean_text(text):
    text = text.lower()
    return re.sub(r'\s+', ' ', text)

def extract_skills(text, skill_list, fuzzy=True, threshold=85):
    text = clean_text(text)
    skills_found = [skill for skill in skill_list if re.search(r'\b' + re.escape(skill) + r'\b', text)]

    if fuzzy:
        for skill in skill_list:
            if skill not in skills_found:
                score = fuzz.partial_ratio(skill, text)
                if score >= threshold:
                    skills_found.append(skill)

    return list(set(skills_found))

def extract_experience(text):
    pattern = r'(\d{1,2}\+?\s*(?:years|yrs|year))'
    return re.findall(pattern, text.lower())

def extract_degrees(text):
    text = text.lower()
    return list({degree for degree in degree_list if re.search(r'\b' + re.escape(degree) + r'\b', text)})

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ''
    return text

def plot_skill_match(resume_name, matched_skills, skill_gaps):
    labels = ['Matched Skills', 'Skill Gaps']
    sizes = [len(matched_skills), len(skill_gaps)]
    colors = ['#4CAF50', '#FF5733']

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    ax.set_title(f'Skill Match for {resume_name}')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)

# ---- Main processing ----
def process_resumes(jd_text, resumes_dir):
    required_skills = extract_skills(jd_text, skill_list)
    if not required_skills:
        return "❌ No skills detected in JD.", pd.DataFrame(), None

    all_results = []
    first_plot = None

    for file_name in os.listdir(resumes_dir):
        if not file_name.endswith('.pdf'):
            continue

        full_path = os.path.join(resumes_dir, file_name)
        text = extract_text_from_pdf(full_path)

        skills = extract_skills(text, skill_list)
        experience = extract_experience(text)
        degrees = extract_degrees(text)

        matched_skills = [s for s in skills if s in required_skills]
        skill_gaps = [s for s in required_skills if s not in skills]
        match_pct = round((len(matched_skills) / len(required_skills)) * 100, 2)

        if first_plot is None:
            first_plot = plot_skill_match(file_name, matched_skills, skill_gaps)

        all_results.append({
            'Resume': file_name,
            'Match %': match_pct,
            'Matched Skills': matched_skills,
            'Skill Gaps': skill_gaps,
            'Experience': experience,
            'Degrees': degrees
        })

    df = pd.DataFrame(all_results)
    df_sorted = df.sort_values(by='Match %', ascending=False).reset_index(drop=True)
    summary = df_sorted[['Resume', 'Match %', 'Matched Skills', 'Skill Gaps', 'Experience', 'Degrees']].to_string(index=False)
    return summary, df_sorted, first_plot

# ---- Gradio Interface ----
def run_app(jd_text, resume_folder):
    with tempfile.TemporaryDirectory() as tmp_dir:
        for file in resume_folder:
            shutil.copy(file.name, tmp_dir)
        summary, df, plot_img = process_resumes(jd_text, tmp_dir)
        return summary, df, plot_img

with gr.Blocks() as demo:
    gr.Markdown("## 📄 Resume-JD Matcher with Skill Visualizer")
    jd_input = gr.Textbox(lines=10, label="Paste Job Description")
    resume_folder = gr.File(file_types=[".pdf"], file_count="multiple", label="Upload Resumes (PDFs)")
    run_btn = gr.Button("Match Resumes")

    output_text = gr.Textbox(label="Matching Summary")
    output_table = gr.Dataframe(label="Detailed Match Table")
    output_img = gr.Image(label="Skill Match Pie Chart")

    run_btn.click(fn=run_app,
                  inputs=[jd_input, resume_folder],
                  outputs=[output_text, output_table, output_img])

# Required for Render
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=10000)

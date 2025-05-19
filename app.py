import os
import re
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from fuzzywuzzy import fuzz
import gradio as gr
from io import BytesIO

matplotlib.use('Agg')  # Use non-GUI backend for matplotlib (important for Render)

# Master skill list
skill_list = ['python', 'machine learning', 'deep learning', 'sql', 'aws', 'numpy',
              'javascript', 'c++', 'c', 'html', 'css', 'nlp', 'react', 'java',
              'excel', 'pandas', 'tensorflow', 'web scraping', 'google colab']

# Degree list
degree_list = ['bachelor', 'b.tech', 'm.tech', 'msc', 'mba', 'bsc', 'phd', 'doctorate',
               'master', "master's", "bachelor's", "int. msc", "b.sc", "m.sc"]

def clean_text(text):
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text

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
    exp_pattern = r'(\d{1,2}\+?\s*(?:years|yrs|year))'
    return re.findall(exp_pattern, text.lower())

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

def plot_overall_ranking(df_sorted):
    plt.figure(figsize=(10, 6))
    plt.barh(df_sorted['Resume'], df_sorted['Match %'], color='#4CAF50')
    plt.xlabel('Match Percentage')
    plt.title('Ranking of Resumes by Skill Match')
    plt.gca().invert_yaxis()

    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf

def process_resumes(jd_input, uploaded_resumes):
    required_skills = extract_skills(jd_input, skill_list)

    if not required_skills:
        return "No skills found in JD.", None, None

    all_results = []

    for resume_file in uploaded_resumes:
        path = resume_file.name  # Gradio gives a NamedString with .name
        text = extract_text_from_pdf(path)

        skills = extract_skills(text, skill_list)
        experience = extract_experience(text)
        degrees = extract_degrees(text)

        matched_skills = [skill for skill in skills if skill in required_skills]
        skill_gaps = [skill for skill in required_skills if skill not in skills]

        match_percentage = round((len(matched_skills) / len(required_skills)) * 100, 2)

        all_results.append({
            'Resume': os.path.basename(path),
            'Match %': match_percentage,
            'Matched Skills': ", ".join(matched_skills),
            'Skill Gaps': ", ".join(skill_gaps),
            'Experience': ", ".join(experience),
            'Degrees': ", ".join(degrees),
        })

    df = pd.DataFrame(all_results)
    df_sorted = df.sort_values(by='Match %', ascending=False).reset_index(drop=True)

    graph = plot_overall_ranking(df_sorted)

    return "✅ Ranking complete!", df_sorted, graph

with gr.Blocks() as app:
    gr.Markdown("# 📄 Resume Matcher App")
    gr.Markdown("Upload resumes and paste a job description to find the best matches.")

    jd_input = gr.Textbox(lines=10, label="Job Description")
    resumes_input = gr.File(file_types=[".pdf"], file_count="multiple", label="Upload Resumes (PDF)")

    btn = gr.Button("Run Matching")
    output_text = gr.Textbox(label="Status")
    output_table = gr.Dataframe(label="Ranked Results")
    output_plot = gr.Image(label="Resume Ranking Graph")

    def run_pipeline(jd_input, resumes_input):
        return process_resumes(jd_input, resumes_input)

    btn.click(fn=run_pipeline,
              inputs=[jd_input, resumes_input],
              outputs=[output_text, output_table, output_plot])

# For Render, must call app.launch() only if this is main
if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=10000)



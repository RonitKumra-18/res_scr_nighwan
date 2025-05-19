import os
import re
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from fuzzywuzzy import fuzz
from tkinter import Tk, filedialog, Text, Label, Button, Scrollbar, RIGHT, Y, END
from tkinter.messagebox import showinfo
import tkinter as tk

skill_list = ['python', 'machine learning', 'deep learning', 'sql', 'aws', 'numpy',
              'javascript', 'c++', 'c', 'html', 'css', 'nlp', 'react', 'java', 
              'excel', 'pandas', 'tensorflow', 'web scraping', 'google colab']

degree_list = ['bachelor', 'b.tech', 'm.tech', 'msc', 'mba', 'bsc', 'phd', 'doctorate', 'master',
               "master's", "bachelor's", "int. msc", "b.sc", "m.sc"]

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

def plot_ranking_chart(df):
    plt.figure(figsize=(10, 5))
    plt.barh(df['Resume'], df['Match %'], color='skyblue')
    plt.xlabel('Match %')
    plt.title('Resume Ranking by Skill Match')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.show()

def process_resumes(jd_text, folder_path):
    required_skills = extract_skills(jd_text, skill_list)
    if not required_skills:
        return "No skills detected in JD.", None

    all_results = []
    resume_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]

    for resume_file in resume_files:
        path = os.path.join(folder_path, resume_file)
        text = extract_text_from_pdf(path)
        skills = extract_skills(text, skill_list)
        experience = extract_experience(text)
        degrees = extract_degrees(text)
        matched_skills = [skill for skill in skills if skill in required_skills]
        skill_gaps = [skill for skill in required_skills if skill not in skills]
        match_percentage = round((len(matched_skills) / len(required_skills)) * 100, 2)

        all_results.append({
            'Resume': resume_file,
            'Match %': match_percentage,
            'Matched Skills': matched_skills,
            'Skill Gaps': skill_gaps,
            'Experience': experience,
            'Degrees': degrees
        })

    df = pd.DataFrame(all_results)
    df_sorted = df.sort_values(by='Match %', ascending=False).reset_index(drop=True)

    output = "====== Ranked Resumes by Skill Match % ======\n"
    for i, row in df_sorted.iterrows():
        output += f"\n{row['Resume']}\nMatch %: {row['Match %']}\nSkills: {row['Matched Skills']}\nExperience: {row['Experience']}\nDegrees: {row['Degrees']}\n"

    return output, df_sorted

def select_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        folder_label.config(text=f"Resumes Folder: {folder_path}")
        app.folder_path = folder_path

def run_matching():
    jd_text = jd_entry.get("1.0", END)
    if not hasattr(app, 'folder_path') or not jd_text.strip():
        showinfo("Input Missing", "Please provide both JD and resume folder.")
        return

    result_text.delete("1.0", END)
    output, df = process_resumes(jd_text, app.folder_path)
    result_text.insert(END, output)
    if df is not None:
        plot_ranking_chart(df)

# GUI Setup
app = Tk()
app.title("Resume Ranker")
app.geometry("800x700")

Label(app, text="Paste Job Description:").pack()

jd_entry = Text(app, height=10, width=100)
jd_entry.pack()

Button(app, text="Select Resume Folder", command=select_folder).pack(pady=5)
folder_label = Label(app, text="No folder selected")
folder_label.pack()

Button(app, text="Run Matching", command=run_matching).pack(pady=10)

Label(app, text="Results:").pack()

result_frame = tk.Frame(app)
result_frame.pack(fill='both', expand=True)

scrollbar = Scrollbar(result_frame)
scrollbar.pack(side=RIGHT, fill=Y)

result_text = Text(result_frame, height=20, width=100, yscrollcommand=scrollbar.set)
result_text.pack(side='left', fill='both', expand=True)
scrollbar.config(command=result_text.yview)

app.mainloop()

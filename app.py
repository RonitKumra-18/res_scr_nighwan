import os
import io
import re
import shutil
import tempfile
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
from fuzzywuzzy import fuzz

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ray import serve

import ray
import base64

# ----------------- Start Ray and Serve -----------------
ray.init(ignore_reinit_error=True)
serve.start(detached=True)

# ----------------- FastAPI App -----------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Config -----------------
skill_list = ['python', 'machine learning', 'deep learning', 'sql', 'aws', 'numpy',
              'javascript', 'c++', 'c', 'html', 'css', 'nlp', 'react', 'java',
              'excel', 'pandas', 'tensorflow', 'web scraping', 'google colab']

degree_list = ['bachelor', 'b.tech', 'm.tech', 'msc', 'mba', 'bsc', 'phd', 'doctorate',
               'master', "master's", "bachelor's", "int. msc", "b.sc", "m.sc"]

# ----------------- Helper Functions -----------------
def clean_text(text):
    return re.sub(r'\s+', ' ', text.lower())

def extract_skills(text, skill_list, fuzzy=True, threshold=85):
    text = clean_text(text)
    found = [skill for skill in skill_list if re.search(r'\b' + re.escape(skill) + r'\b', text)]

    if fuzzy:
        for skill in skill_list:
            if skill not in found and fuzz.partial_ratio(skill, text) >= threshold:
                found.append(skill)

    return list(set(found))

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
            page_text = page.extract_text()
            if page_text:
                text += page_text
    return text

def plot_match_bar_chart(results_df):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(results_df['Resume'], results_df['Match %'], color='#4CAF50')
    ax.set_xlabel("Resumes")
    ax.set_ylabel("Match Percentage")
    ax.set_title("Skill Match Percentage")
    ax.set_ylim(0, 100)
    plt.xticks(rotation=45, ha='right')

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)

    encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{encoded}"

# ----------------- Serve Deployment -----------------
@serve.deployment(route_prefix="/match")
@serve.ingress(app)
class ResumeMatcher:

    @app.post("/")
    async def match_resumes(self, jd: str = Form(...), files: list[UploadFile] = File(...)):
        required_skills = extract_skills(jd, skill_list)
        if not required_skills:
            return JSONResponse({"error": "❌ No skills detected in job description."}, status_code=400)

        all_results = []

        with tempfile.TemporaryDirectory() as tmpdir:
            for file in files:
                file_path = os.path.join(tmpdir, file.filename)
                with open(file_path, "wb") as f:
                    f.write(await file.read())

                text = extract_text_from_pdf(file_path)
                skills = extract_skills(text, skill_list)
                experience = extract_experience(text)
                degrees = extract_degrees(text)

                matched = [s for s in skills if s in required_skills]
                match_pct = round(len(matched) / len(required_skills) * 100, 2)
                gaps = [s for s in required_skills if s not in skills]

                all_results.append({
                    "Resume": file.filename,
                    "Match %": match_pct,
                    "Matched Skills": matched,
                    "Skill Gaps": gaps,
                    "Experience": experience,
                    "Degrees": degrees
                })

        df = pd.DataFrame(all_results).sort_values(by="Match %", ascending=False).reset_index(drop=True)
        plot_url = plot_match_bar_chart(df)

        return {
            "summary": df.to_dict(orient="records"),
            "chart": plot_url
        }

# ----------------- Deploy on Start -----------------
ResumeMatcher.deploy()

# ----------------- For Render -----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000)

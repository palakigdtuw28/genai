import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
import hashlib
from dotenv import load_dotenv
from docx import Document
import pdfplumber
from io import BytesIO
import requests

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

USER_DATA_FILE = "user_data.csv"

# --- Helper functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def save_user(full_name, email, username, password):
    hashed_pw = hash_password(password)
    new_user = pd.DataFrame([[full_name, email, username, hashed_pw]],
                            columns=["Full Name", "Email", "Username", "Password"])
    if os.path.exists(USER_DATA_FILE):
        df = pd.read_csv(USER_DATA_FILE)
        df = pd.concat([df, new_user], ignore_index=True)
    else:
        df = new_user
    df.to_csv(USER_DATA_FILE, index=False)

def authenticate(username, password):
    if not os.path.exists(USER_DATA_FILE):
        return False
    df = pd.read_csv(USER_DATA_FILE)
    hashed_pw = hash_password(password)
    return ((df["Username"] == username) & (df["Password"] == hashed_pw)).any()

def extract_text_from_pdf(file):
    with pdfplumber.open(BytesIO(file.read())) as pdf:
        return "\n".join([page.extract_text() or '' for page in pdf.pages])

def extract_text_from_docx(file):
    doc = Document(BytesIO(file.read()))
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

def extract_resume_text(file):
    if file.type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(file)
    else:
        return ""

# --- App logic ---
st.set_page_config(page_title="Pathfinder Career Assistant", layout="centered")
st.title("🔐 Pathfinder - Login / Registration")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""

mode = st.radio("Choose Option", ["Login", "Register"])

if mode == "Register":
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Register"):
        if password != confirm_password:
            st.warning("Passwords do not match.")
        else:
            save_user(full_name, email, username, password)
            st.success("Registration successful. Please login.")

elif mode == "Login":
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(username, password):
            st.success("Login successful!")
            st.session_state.authenticated = True
        else:
            st.error("Invalid credentials.")

# --- Post-login views ---
if st.session_state.authenticated:
    st.sidebar.title("📌 Navigation")
    page = st.sidebar.radio("Go to", ["Resume Analysis", "Skill Gap Analyzer", "Job Search"])

    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])
    if uploaded_file:
        st.session_state.resume_text = extract_resume_text(uploaded_file)

    if page == "Resume Analysis":
        st.subheader("📄 Resume Analyzer")
        if st.session_state.resume_text:
            prompt = f"Analyze this resume and provide a summary of skills, experience, and suggestions:\n\n{st.session_state.resume_text}"
            result = model.generate_content(prompt)
            st.write(result.text)
        else:
            st.info("Please upload your resume from the sidebar.")

    elif page == "Skill Gap Analyzer":
        st.subheader("🔍 Skill Gap Analyzer")
        if st.session_state.resume_text:
            role = st.text_input("Desired Job Role", placeholder="e.g., Data Scientist")
            if st.button("Analyze Skill Gap"):
                prompt = f"You are a career coach. Analyze the resume for skill gaps for the role '{role}'.\n\nResume:\n{st.session_state.resume_text}"
                result = model.generate_content(prompt)
                st.write(result.text)
        else:
            st.info("Please upload your resume from the sidebar.")

    elif page == "Job Search":
        st.subheader("💼 Job Search")
        role = st.text_input("Job Title", placeholder="e.g., Software Developer")
        location = st.text_input("Location", placeholder="e.g., Delhi")
        if st.button("Search Jobs"):
            url = "https://jsearch.p.rapidapi.com/search"
            params = {"query": f"{role} in {location}", "page": "1", "num_pages": "1"}
            headers = {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": RAPIDAPI_HOST,
            }
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                jobs = response.json().get("data", [])
                for job in jobs:
                    st.markdown(f"**{job['job_title']}** at *{job['employer_name']}*")
                    st.write(job["job_description"][:300] + "...")
                    st.markdown(f"[Apply Here]({job['job_apply_link']})")
                    st.markdown("---")
            else:
                st.error("Failed to fetch job results. Check API credentials.")
                    

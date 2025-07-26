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
SAVED_RESUMES_FILE = "saved_resumes.csv"

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

def save_resume(username, text):
    if username == "guest":
        return
    new_data = pd.DataFrame([[username, text]], columns=["Username", "ResumeText"])
    if os.path.exists(SAVED_RESUMES_FILE):
        df = pd.read_csv(SAVED_RESUMES_FILE)
        df = df[df["Username"] != username]
        df = pd.concat([df, new_data], ignore_index=True)
    else:
        df = new_data
    df.to_csv(SAVED_RESUMES_FILE, index=False)

def load_resume(username):
    if not os.path.exists(SAVED_RESUMES_FILE):
        return ""
    df = pd.read_csv(SAVED_RESUMES_FILE)
    row = df[df["Username"] == username]
    if not row.empty:
        return row.iloc[0]["ResumeText"]
    return ""

# --- Page Config ---
st.set_page_config(page_title="Pathfinder Career Assistant", layout="centered")
st.title("🎯 Pathfinder AI Career Assistant")

# --- Session state setup ---
for key in ["authenticated", "username", "resume_text", "mode", "show_form"]:
    if key not in st.session_state:
        st.session_state[key] = None

if st.session_state.authenticated is None:
    st.session_state.authenticated = False
if st.session_state.show_form is None:
    st.session_state.show_form = True
if st.session_state.mode is None:
    st.session_state.mode = "Login"
    # --- Login / Register / Guest UI ---
if not st.session_state.authenticated and st.session_state.show_form:
    st.session_state.mode = st.radio("Choose Option", ["Login", "Register", "Guest"])

    if st.session_state.mode == "Register":
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
                st.success("Registration successful! Please log in.")
                st.session_state.mode = "Login"
                st.rerun()

    elif st.session_state.mode == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if authenticate(username, password):
                st.success("Login successful!")
                st.session_state.username = username
                st.session_state.authenticated = True
                st.session_state.show_form = False
                st.rerun()
            else:
                st.error("Invalid credentials.")

    elif st.session_state.mode == "Guest":
        st.info("Continuing in Guest Mode")
        st.session_state.username = "guest"
        st.session_state.authenticated = True
        st.session_state.show_form = False
        st.rerun()
    # --- MAIN APP UI ---
if st.session_state.authenticated:
    tab = st.sidebar.radio("📂 Navigation", ["Resume Analyzer", "Skill Gap Analyzer", "Job Search", "Profile", "Logout"])

    # --- Resume Analyzer ---
    if tab == "Resume Analyzer":
        st.subheader("📄 Resume Analyzer")
        uploaded_file = st.file_uploader("Upload your Resume (PDF or DOCX)", type=["pdf", "docx"])

        if uploaded_file:
            resume_text = extract_resume_text(uploaded_file)
            st.session_state.resume_text = resume_text
            save_resume(st.session_state.username, resume_text)
            st.success("Resume text extracted and saved!")

        elif st.session_state.resume_text == "":
            st.session_state.resume_text = load_resume(st.session_state.username)

        if st.session_state.resume_text:
            st.text_area("Resume Content", value=st.session_state.resume_text, height=300)

            if st.button("Analyze Resume"):
                prompt = f"Analyze this resume and give feedback on strengths, weaknesses, and suggest improvements:\n\n{st.session_state.resume_text}"
                response = model.generate_content(prompt)
                st.subheader("🧾 Resume Analysis")
                st.markdown(response.text)

    # --- Skill Gap Analyzer ---
    elif tab == "Skill Gap Analyzer":
        st.subheader("🧠 Skill Gap Analyzer")
        job_title = st.text_input("Enter the Job Role you're targeting (e.g., Data Scientist)")

        if st.button("Analyze Skill Gaps"):
            if not st.session_state.resume_text:
                st.warning("Please upload your resume in the Resume Analyzer tab first.")
            elif not job_title:
                st.warning("Please enter a job role.")
            else:
                prompt = (
                    f"Based on this resume:\n{st.session_state.resume_text}\n\n"
                    f"What are the skill gaps for the role of {job_title}? Suggest what to learn to be job ready."
                )
                response = model.generate_content(prompt)
                st.subheader("🧠 Skill Gap Report")
                st.markdown(response.text)
    # --- Job Search ---
    elif tab == "Job Search":
        st.subheader("💼 Job Search")
        keyword = st.text_input("Job Keyword", placeholder="e.g., Python Developer")
        location = st.text_input("Location", placeholder="e.g., Delhi, India")
        if st.button("Search Jobs"):
            if keyword.strip() == "":
                st.warning("Please enter a keyword to search.")
            else:
                url = "https://jsearch.p.rapidapi.com/search"
                querystring = {
                    "query": f"{keyword} in {location or 'India'}",
                    "num_pages": "1"
                }
                headers = {
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": RAPIDAPI_HOST
                }
                try:
                    response = requests.get(url, headers=headers, params=querystring)
                    jobs = response.json().get("data", [])
                    if jobs:
                        for job in jobs:
                            st.markdown(f"### {job.get('job_title')}")
                            st.markdown(f"**Company:** {job.get('employer_name')}")
                            st.markdown(f"**Location:** {job.get('job_city')}, {job.get('job_country')}")
                            st.markdown(f"**Apply Link:** [Click here]({job.get('job_apply_link')})")
                            st.markdown("---")
                    else:
                        st.info("No jobs found for the given search.")
                except Exception as e:
                    st.error(f"API Error: {e}")

    # --- Profile Page ---
    elif tab == "Profile":
        st.subheader("👤 User Profile")
        if st.session_state.username == "guest":
            st.info("You're in Guest Mode. No personal data saved.")
        else:
            df = pd.read_csv(USER_DATA_FILE)
            user_row = df[df["Username"] == st.session_state.username]
            if not user_row.empty:
                user_info = user_row.iloc[0]
                st.write(f"**Full Name:** {user_info['Full Name']}")
                st.write(f"**Email:** {user_info['Email']}")
                st.write(f"**Username:** {user_info['Username']}")

    # --- Logout ---
    elif tab == "Logout":
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.resume_text = ""
        st.session_state.show_form = True
        st.success("Logged out successfully.")
        st.rerun()

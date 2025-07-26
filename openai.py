import streamlit as st
import os
import hashlib
import requests
from dotenv import load_dotenv
from streamlit_mic_recorder import speech_to_text
import google.generativeai as genai
import pdfplumber
from docx import Document
from io import BytesIO

# Load keys
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Session State Initialization
for key in ["users", "logged_in", "username", "chat_history"]:
    if key not in st.session_state:
        st.session_state[key] = {} if key == "users" else [] if key == "chat_history" else False if key == "logged_in" else None

# Password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Auth screen
def auth_ui():
    st.set_page_config(page_title="Pathfinder", layout="centered")
    st.title("🧭 Pathfinder - Career Assistant")
    st.markdown("### Login or Register")

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username in st.session_state.users and st.session_state.users[username] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("✅ Logged in successfully")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

    with tab2:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Register"):
            if new_user in st.session_state.users:
                st.warning("⚠️ Username already exists")
            else:
                st.session_state.users[new_user] = hash_password(new_pass)
                st.success("✅ Registered! Please log in")

# Resume Analyzer
def resume_analyzer_ui():
    st.subheader("📄 Resume Analyzer")
    uploaded_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"])

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            with pdfplumber.open(BytesIO(uploaded_file.read())) as pdf:
                resume_text = "\n".join(page.extract_text() or '' for page in pdf.pages)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(BytesIO(uploaded_file.read()))
            resume_text = "\n".join([para.text for para in doc.paragraphs])
        else:
            st.error("Unsupported file format")
            return

        st.text_area("Extracted Resume Text", resume_text, height=200)

        if st.button("Analyze Resume"):
            with st.spinner("Analyzing..."):
                try:
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    prompt = f"Analyze this resume and list key skills:\n\n{resume_text}"
                    response = model.generate_content(prompt)
                    st.success("✅ Analysis complete")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error: {e}")

# Skill Gap Analyzer
def skill_gap_ui():
    st.subheader("📊 Skill Gap Analyzer")
    resume_text = st.text_area("Paste your resume text", height=200)
    job_description = st.text_area("Paste a job description", height=200)

    if st.button("Find Skill Gaps"):
        with st.spinner("Analyzing..."):
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                prompt = (
                    f"Compare the following resume to the job description and highlight missing or weak skills.\n\n"
                    f"Resume:\n{resume_text}\n\nJob Description:\n{job_description}"
                )
                response = model.generate_content(prompt)
                st.success("✅ Skill gap analysis complete")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {e}")

# Job Search
def job_search_ui():
    st.subheader("🔎 Job Search")
    query = st.text_input("Enter job title and location (e.g., 'Software Developer in Mumbai')")

    if st.button("Search"):
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        params = {"query": query, "page": "1", "num_pages": "1"}

        try:
            res = requests.get("https://jsearch.p.rapidapi.com/search", headers=headers, params=params)
            jobs = res.json().get("data", [])
            if not jobs:
                st.info("No jobs found.")
            for job in jobs:
                st.markdown(f"### 💼 {job['job_title']} at {job['employer_name']}")
                st.markdown(f"📍 {job['job_city']}, {job['job_country']}")
                st.markdown(f"[🔗 Apply Here]({job['job_apply_link']})")
                st.markdown("---")
        except Exception as e:
            st.error(f"Error: {e}")

# Chatbot with mic
def ask_pathfinder():
    st.subheader("💬 Ask Pathfinder (Chatbot with Mic)")

    mic_text = speech_to_text(language='en', use_container_width=True)
    user_query = st.chat_input("Ask a career-related question...")
    if mic_text:
        user_query = mic_text

    for chat in reversed(st.session_state.chat_history):
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])

    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(user_query)
                reply = response.text
            except Exception as e:
                reply = f"❌ Error: {e}"
            st.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

# Main app layout
def main_app():
    st.set_page_config(page_title="Pathfinder", layout="wide")
    st.sidebar.title("🧭 Pathfinder")
    st.sidebar.markdown(f"👤 Logged in as: `{st.session_state.username}`")

    tab = st.sidebar.radio("Navigation", [
        "Resume Analyzer", "Skill Gap Analyzer", "Job Search", "Ask Pathfinder", "Logout"
    ])

    if tab == "Resume Analyzer":
        resume_analyzer_ui()
    elif tab == "Skill Gap Analyzer":
        skill_gap_ui()
    elif tab == "Job Search":
        job_search_ui()
    elif tab == "Ask Pathfinder":
        ask_pathfinder()
    elif tab == "Logout":
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.chat_history.clear()
        st.success("Logged out successfully.")
        st.rerun()

# Entry point
if not st.session_state.logged_in:
    auth_ui()
else:
    main_app()
                     

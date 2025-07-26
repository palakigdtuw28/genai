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

# --- Load environment variables ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# --- Initialize session state ---
for key in ["users", "logged_in", "username", "chat_history"]:
    if key not in st.session_state:
        st.session_state[key] = {} if key == "users" else [] if key == "chat_history" else False if key == "logged_in" else None

# --- Helper: Hash passwords ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Auth UI ---
def auth_ui():
    st.set_page_config(page_title="Pathfinder", layout="centered")
    st.title("🧭 Pathfinder - Career AI Assistant")
    st.markdown("#### Login or Register to continue")

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username in st.session_state.users and st.session_state.users[username] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials.")

    with tab2:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Register"):
            if new_user in st.session_state.users:
                st.warning("⚠️ Username already exists.")
            else:
                st.session_state.users[new_user] = hash_password(new_pass)
                st.success("✅ Registered! Please login.")

# --- Resume Analyzer ---
def resume_analyzer_ui():
    st.subheader("📄 Resume Analyzer")
    uploaded_file = st.file_uploader("Upload your Resume (PDF or DOCX)", type=["pdf", "docx"])
    
    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            with pdfplumber.open(BytesIO(uploaded_file.read())) as pdf:
                resume_text = "\n".join(page.extract_text() or '' for page in pdf.pages)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(BytesIO(uploaded_file.read()))
            resume_text = "\n".join([para.text for para in doc.paragraphs])
        else:
            st.error("Unsupported file format.")
            return
        
        st.markdown("#### 📑 Extracted Resume Text")
        st.text_area("Resume Preview", resume_text, height=200)

        if st.button("Analyze Resume"):
            with st.spinner("Analyzing..."):
                try:
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    prompt = f"Analyze this resume and list the key skills:\n\n{resume_text}"
                    response = model.generate_content(prompt)
                    st.success("✅ Analysis complete!")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error analyzing resume: {e}")

# --- Skill Gap Analyzer ---
def skill_gap_ui():
    st.subheader("📊 Skill Gap Analyzer")
    resume_input = st.text_area("Paste your resume text here", height=200)
    job_description = st.text_area("Paste a job description", height=200)

    if st.button("Compare Skills"):
        with st.spinner("Analyzing..."):
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                prompt = (
                    f"Compare this resume to the job description and identify any skill gaps.\n\n"
                    f"Resume:\n{resume_input}\n\nJob Description:\n{job_description}"
                )
                response = model.generate_content(prompt)
                st.success("✅ Comparison complete!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {e}")

# --- Job Search UI ---
def job_search_ui():
    st.subheader("🔎 Job Search")
    query = st.text_input("Search (e.g. Data Analyst in Bangalore)")
    if st.button("Search Jobs"):
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
            st.error(f"API Error: {e}")

# --- Ask Pathfinder (Chatbot + Mic) ---
def ask_pathfinder():
    st.subheader("💬 Ask Pathfinder (Career Chatbot)")
    mic_input = speech_to_text(language='en', use_container_width=True)
    user_input = st.chat_input("Ask anything about your career...")
    if mic_input:
        user_input = mic_input

    for chat in reversed(st.session_state.chat_history):
        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(user_input)
                reply = response.text
            except Exception as e:
                reply = f"❌ Error: {e}"
            st.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

# --- Main App Layout ---
def main_app():
    st.set_page_config(page_title="Pathfinder", layout="wide")
    st.sidebar.title("🧭 Pathfinder Menu")
    st.sidebar.markdown(f"👤 Logged in as: `{st.session_state.username}`")

    choice = st.sidebar.radio("Choose a Tool", [
        "Resume Analyzer", "Skill Gap Analyzer", "Job Search", "Ask Pathfinder", "Logout"
    ])

    if choice == "Resume Analyzer":
        resume_analyzer_ui()
    elif choice == "Skill Gap Analyzer":
        skill_gap_ui()
    elif choice == "Job Search":
        job_search_ui()
    elif choice == "Ask Pathfinder":
        ask_pathfinder()
    elif choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.chat_history.clear()
        st.success("Logged out successfully.")
        st.rerun()

# --- Entry Point ---
if not st.session_state.logged_in:
    auth_ui()
else:
    main_app()
        

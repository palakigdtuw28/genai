import streamlit as st
import os
import google.generativeai as genai
import pdfplumber
from dotenv import load_dotenv
from docx import Document
from io import BytesIO
from streamlit_mic_recorder import speech_to_text

# --- Load Environment Variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Session State Initialization ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

# --- Simulated User Database ---
user_db = {"guest": "guest"}  # Add guest login

def extract_resume_text(file):
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)
    return ""

def login_ui():
    st.markdown("## 👩🏻‍🎓 **Pathfinder**", unsafe_allow_html=True)
    st.markdown("### Choose an option:")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔐 Login"):
            st.session_state.auth_mode = "login"
    with col2:
        if st.button("📝 Register"):
            st.session_state.auth_mode = "register"
    with col3:
        if st.button("🚪 Guest"):
            st.session_state.authenticated = True
            st.session_state.username = "Guest"
            return

    mode = st.session_state.get("auth_mode", "login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "register":
        if st.button("Register"):
            if username in user_db:
                st.warning("Username already exists.")
            else:
                user_db[username] = password
                st.success("Registered successfully. Please log in.")
                st.session_state.auth_mode = "login"

    elif mode == "login":
        if st.button("Login"):
            if user_db.get(username) == password:
                st.session_state.authenticated = True
                st.session_state.username = username
            else:
                st.error("Invalid credentials.")

def main_app():
    with st.sidebar:
        tab = st.radio("📌 Navigation", ["Ask 🤖", "Resume Analyzer", "Skill Gap Analyzer", "Job Search"], key="main_tabs")

    st.markdown(
        """
        <style>
            div[data-testid="stSidebarNav"] ul {
                padding-bottom: 80px;
            }
            .sidebar-bottom {
                position: fixed;
                bottom: 20px;
                left: 10px;
                font-size: 16px;
            }
        </style>
        <div class="sidebar-bottom">
            👤 <b>{}</b> &nbsp; | &nbsp; 🔓 <a href="/?logout=true">Logout</a>
        </div>
        """.format(st.session_state.username), unsafe_allow_html=True)

    if tab == "Ask 🤖":
        st.title("💬 Ask Pathfinder")
        text = speech_to_text(language="en")
        user_input = st.text_input("Ask your question (or use mic above):", value=text if text else "")
        if st.button("Ask") and user_input:
            with st.spinner("Thinking..."):
                response = model.generate_content(user_input)
                st.markdown(response.text)

    elif tab == "Resume Analyzer":
        st.title("📄 Resume Analyzer")
        method = st.radio("Choose input method:", ["Upload Resume", "Enter Manually"])

        if method == "Upload Resume":
            uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
            if uploaded_file:
                st.session_state.resume_text = extract_resume_text(uploaded_file)
                st.success("Resume text extracted successfully.")
        else:
            st.session_state.resume_text = st.text_area("Paste your resume text below:")

        if st.session_state.resume_text:
            if st.button("Analyze Resume"):
                with st.spinner("Analyzing your resume..."):
                    prompt = (
                        "You are a career expert reviewing a candidate's resume.\n\n"
                        "Analyze the following resume text and provide:\n"
                        "1. Summary of strengths\n"
                        "2. Weaknesses or areas for improvement\n"
                        "3. Suggestions to improve this resume\n\n"
                        f"Resume:\n{st.session_state.resume_text}"
                    )
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
        else:
            st.info("Please provide resume content by uploading or entering manually.")

    elif tab == "Skill Gap Analyzer":
        st.title("📊 Skill Gap Analyzer")
        job_title = st.text_input("Target Job Role", placeholder="e.g., Frontend Developer")

        if job_title and st.session_state.resume_text:
            if st.button("Analyze Skill Gap"):
                with st.spinner("Analyzing skill gaps..."):
                    prompt = (
                        f"You are an expert in career development.\n"
                        f"Compare the following resume against the job role: {job_title}.\n"
                        f"Provide:\n"
                        f"1. Key skills required for {job_title}\n"
                        f"2. Skills present and missing from the resume\n"
                        f"3. Learning resources to fill the skill gap\n\n"
                        f"Resume:\n{st.session_state.resume_text}"
                    )
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
        else:
            st.info("Please enter a job title and provide your resume in the previous section.")

    elif tab == "Job Search":
        st.title("💼 Job Search")
        title = st.text_input("Enter Job Title", placeholder="e.g., Data Analyst")
        location = st.text_input("Enter Location", placeholder="e.g., Delhi")

        if st.button("Search Jobs") and title:
            with st.spinner("Searching jobs..."):
                prompt = (
                    f"Suggest job listings with company names and brief roles for the title '{title}' in location '{location}'."
                )
                response = model.generate_content(prompt)
                st.markdown(response.text)

# --- App Execution ---
if st.query_params.get("logout"):
    st.session_state.authenticated = False
    st.session_state.username = ""

if st.session_state.authenticated:
    main_app()
else:
    login_ui()
    

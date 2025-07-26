# pathfinder_app.py (Part 1)

import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
import pdfplumber
from docx import Document
from streamlit_mic_recorder import speech_to_text

# --- Load environment and configure API ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# --- Model Setup ---
if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
model = st.session_state.gemini_model
# pathfinder_app.py (Part 2)

def extract_resume_text(file):
    """Extracts text from PDF or DOCX files."""
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(para.text for para in doc.paragraphs if para.text)
    return ""

def clear_session():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_rerun()
# pathfinder_app.py (Part 3)

def init_session():
    defaults = {
        "authenticated": False,
        "guest": False,
        "username": "",
        "resume_text": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

def login_ui():
    st.title("🔐 Pathfinder Login")
    mode = st.radio("Choose mode", ["Login", "Guest"])
    if mode == "Login":
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login") and user == "admin" and pwd == "admin":
            st.session_state.authenticated = True
            st.session_state.username = user
            st.success("Logged in")
    else:
        if st.button("Continue as Guest"):
            st.session_state.authenticated = True
            st.session_state.guest = True
            st.session_state.username = "Guest"

    st.stop()

if not st.session_state.authenticated:
    login_ui()

# Sidebar
with st.sidebar:
    st.title("🧭 Pathfinder")
    section = st.radio("Go to", [
        "📄 Resume Analyzer", 
        "📊 Skill Gap Analyzer", 
        "🤖 Ask AI", 
        "💼 Job Search"
    ])
    
    st.markdown("---")
    st.markdown(f"**👤 User:** {st.session_state.username}")
    if st.button("🔓 Logout"):
        clear_session()
# pathfinder_app.py (Part 4)

if section == "📄 Resume Analyzer":
    st.header("📄 Resume Analyzer")
    input_method = st.radio("Choose Input Method", ["Upload Resume", "Enter Manually"])
    
    if input_method == "Upload Resume":
        resume_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
        if resume_file:
            st.session_state.resume_text = extract_resume_text(resume_file)
            st.success("Resume text extracted!")

    else:
        st.session_state.resume_text = st.text_area("Paste your resume content here")

    if st.session_state.resume_text and st.button("Analyze Resume"):
        with st.spinner("Analyzing..."):
            prompt = (
                "You are a career coach. Analyze the resume below and provide:\n"
                "1. Strengths\n2. Weaknesses\n3. Suggestions\n\n"
                f"{st.session_state.resume_text}"
            )
            result = model.generate_content(prompt)
            st.write(result.text or "❌ No analysis returned.")
            # pathfinder_app.py (Part 5)

elif section == "📊 Skill Gap Analyzer":
    st.header("📊 Skill Gap Analyzer")
    role = st.text_input("Enter your Target Job Role (e.g., Data Scientist)")

    if st.button("Analyze Skill Gaps"):
        if not st.session_state.resume_text:
            st.warning("Please upload or enter resume in the Resume Analyzer section.")
        elif not role.strip():
            st.warning("Please enter a job role.")
        else:
            with st.spinner("Comparing skills..."):
                prompt = (
                    f"Compare the following resume to the job role '{role}'. "
                    "List skills required, skills present, missing skills, and how to learn them:\n\n"
                    f"{st.session_state.resume_text}"
                )
                response = model.generate_content(prompt)
                st.write(response.text or "❌ No result.")
      # pathfinder_app.py (Part 6)

elif section == "🤖 Ask AI":
    st.header("🤖 Ask Pathfinder Chatbot")
    
    mic_input = speech_to_text(language="en", use_container_width=True, just_once=True)
    user_input = mic_input or st.text_input("Ask something:")
    
    if st.button("Ask"):
        if user_input.strip() == "":
            st.warning("Please speak or type a question.")
        else:
            with st.spinner("Generating answer..."):
                response = model.generate_content(user_input)
                st.markdown("**Response:**")
                st.write(response.text or "❌ No response.")
# pathfinder_app.py (Part 7)

elif section == "💼 Job Search":
    st.header("💼 Search for Jobs")
    job_title = st.text_input("Job Title (e.g., Backend Developer)")
    location = st.text_input("Preferred Location (e.g., Delhi)")

    if st.button("Search Jobs"):
        if job_title and location:
            with st.spinner("Searching..."):
                jobs = [
                    {"title": f"{job_title} at TechNova", "loc": location, "url": "https://example.com/job1"},
                    {"title": f"Junior {job_title} at InnovateX", "loc": location, "url": "https://example.com/job2"},
                ]
                for job in jobs:
                    st.markdown(f"**{job['title']}** - {job['loc']}\n[Apply Here]({job['url']})\n---")
        else:
            st.warning("Please provide both job title and location.")
            

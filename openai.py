import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from docx import Document
import pdfplumber
from streamlit_mic_recorder import speech_to_text

# Load API key once
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Load model into session_state once
if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = genai.GenerativeModel("models/gemini-1.5-pro-latest")

model = st.session_state.gemini_model
def extract_resume_text(uploaded_file):
    """Extracts text from PDF or DOCX resume uploads."""
    if uploaded_file.name.lower().endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
    elif uploaded_file.name.lower().endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(para.text for para in doc.paragraphs if para.text).strip()
    return ""
def init_session():
    for key, default in [
        ("authenticated", False),
        ("resume_text", ""),
        ("guest", False),
        ("chat_history", [])
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

init_session()

def show_login():
    st.title("🔐 Pathfinder Access")
    mode = st.radio("Mode:", ["Login", "Guest"])
    if mode == "Login":
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login") and user == "admin" and pwd == "admin":
            st.session_state.authenticated = True
            st.session_state.username = user
            st.success("Logged in!")
    else:
        if st.button("Continue as Guest"):
            st.session_state.authenticated = True
            st.session_state.guest = True
            st.session_state.username = "Guest"
            st.success("Continuing as Guest")

if not st.session_state.authenticated:
    show_login()
    st.stop()
    st.sidebar.title("🧭 Pathfinder Menu")
choice = st.sidebar.selectbox("Go to", [
    "Resume Analyzer", "Skill Gap Analyzer", "Ask 🤖 Chatbot", "Job Search"
])

# Clean bottom position links
st.sidebar.markdown("""
<style>
.sidebar-bottom {
  position: fixed; bottom: 20px; left: 15px; font-size: 16px;
}
</style>
<div class='sidebar-bottom'>
  👤 Profile | 🔓 Logout
</div>
""", unsafe_allow_html=True)
if choice == "Resume Analyzer":
    st.header("📄 Resume Analyzer")
    method = st.radio("Input Method:", ["Upload Resume", "Enter Manually"])
    if method == "Upload Resume":
        file = st.file_uploader("Upload PDF or DOCX", type=["pdf","docx"])
        if file:
            st.session_state.resume_text = extract_resume_text(file)
            st.success("Extracted resume text!")
    else:
        st.session_state.resume_text = st.text_area("Paste your resume here")

    if st.session_state.resume_text and st.button("Analyze Resume"):
        with st.spinner("Analyzing..."):
            prompt = (
                "You are a career expert. Analyze the resume for:\n"
                "1. Strengths\n2. Weaknesses\n3. Suggestions\n\n"
                f"{st.session_state.resume_text}"
            )
            resp = model.generate_content(prompt)
            st.write(resp.text or "⚠️ No result.")
        elif choice == "Skill Gap Analyzer":
    st.header("📊 Skill Gap Analyzer")
    role = st.text_input("Target Role (e.g., Data Analyst)")
    if st.button("Find Skill Gaps"):
        if not st.session_state.resume_text:
            st.warning("Provide resume first.")
        elif not role.strip():
            st.warning("Enter a job role.")
        else:
            with st.spinner("Analyzing gaps..."):
                prompt = (
                    f"Compare the resume against role '{role}' and show:\n"
                    "– Required skills\n– Present skills\n– Missing skills\n– Learning tips\n\n"
                    f"{st.session_state.resume_text}"
                )
                resp = model.generate_content(prompt)
                st.write(resp.text or "⚠️ No result.")
                elif choice == "Ask 🤖 Chatbot":
    st.header("💬 Ask Pathfinder")
    mic_input = speech_to_text(language="en", just_once=True, use_container_width=True)
    user_query = mic_input or st.text_input("Or type your question:")

    if st.button("Ask"):
        if not user_query:
            st.warning("Please speak or type a question.")
        else:
            with st.spinner("Thinking..."):
                resp = model.generate_content(user_query)
                st.write(resp.text or "⚠️ No response.")
elif choice == "Job Search":
    st.header("💼 Job Search")
    role = st.text_input("Job Title")
    location = st.text_input("Location")
    if st.button("Search"):
        if role and location:
            with st.spinner("Searching..."):
                jobs = [
                    {"title":f"{role} at TechNova","loc":location,"link":"https://example.com/1"},
                    {"title":f"Junior {role} at ABC Corp","loc":location,"link":"https://example.com/2"}
                ]
                for job in jobs:
                    st.markdown(f"**{job['title']}** — {job['loc']}\n[Apply]({job['link']})\n---")
        else:
            st.warning("Fill both fields.")

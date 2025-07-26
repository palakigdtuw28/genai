import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
from docx import Document
import pdfplumber
from streamlit_mic_recorder import speech_to_text

# --- Load Environment Variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Configure Gemini ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# --- Helper functions ---
def extract_resume_text(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            return " ".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif uploaded_file.name.endswith(".docx"):
        doc = Document(uploaded_file)
        return " ".join(paragraph.text for paragraph in doc.paragraphs)
    else:
        return ""

# --- Session states ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""
if 'guest_mode' not in st.session_state:
    st.session_state.guest_mode = False

# --- User Authentication ---
def login_page():
    st.title("🔐 Pathfinder Login")
    choice = st.radio("Login or Register", ["Login", "Register", "Continue as Guest"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if choice == "Login":
        if st.button("Login"):
            if username == "admin" and password == "admin":
                st.session_state.authenticated = True
                st.success("Login successful!")
            else:
                st.error("Invalid credentials")
    elif choice == "Register":
        if st.button("Register"):
            st.success("Registration successful. Please login.")
    elif choice == "Continue as Guest":
        st.session_state.guest_mode = True
        st.session_state.authenticated = True

if not st.session_state.authenticated:
    login_page()
    st.stop()

# --- Sidebar Navigation ---
st.sidebar.title("🧭 Pathfinder Navigation")
tab = st.sidebar.radio("Go to", ["Resume Analyzer", "Skill Gap Analyzer", "Ask 🤖", "Job Search"])

# --- Sidebar Bottom UI ---
st.markdown("""
<style>
.sidebar-bottom {
    position: fixed;
    bottom: 20px;
    left: 15px;
    font-size: 16px;
    z-index: 999;
}
</style>
<div class="sidebar-bottom">
    👤 <a href="#profile">Profile</a> &nbsp; | &nbsp; 🔓 <a href="#logout">Logout</a>
</div>
""", unsafe_allow_html=True)

# --- Tabs ---
if tab == "Resume Analyzer":
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

elif tab == "Ask 🤖":
    st.subheader("💬 Ask Pathfinder")
    st.markdown("Ask anything related to careers, jobs, or skills.")
    
    st.markdown("🎙️ Speak your question or type it below:")
    mic_text = speech_to_text(language='en', use_container_width=True, just_once=True, key='ask_pathfinder_mic')
    
    if mic_text:
        st.session_state.query = mic_text
    else:
        st.session_state.query = st.text_input("Your question", key="typed_query")

    if st.button("Ask"):
        if st.session_state.query:
            with st.spinner("Thinking..."):
                response = model.generate_content(st.session_state.query)
                st.markdown("**Response:**")
                st.markdown(response.text)

elif tab == "Job Search":
    st.subheader("💼 Job Search")
    st.markdown("Search for jobs by role and location (sample version)")

    role = st.text_input("Job Title", placeholder="e.g., Software Engineer")
    location = st.text_input("Location", placeholder="e.g., Delhi")

    if st.button("Search Jobs"):
        if role and location:
            with st.spinner("Fetching job listings..."):
                jobs = [
                    {"title": f"{role} at ABC Corp", "location": location, "link": "https://example.com/job1"},
                    {"title": f"Junior {role} at XYZ Ltd", "location": location, "link": "https://example.com/job2"},
                ]
                for job in jobs:
                    st.markdown(f"🔹 **{job['title']}** — *{job['location']}*  \n[Apply Now]({job['link']})")
        else:
            st.warning("Please enter both job title and location.")

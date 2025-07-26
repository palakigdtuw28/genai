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
model = genai.GenerativeModel("gemini-2.0-flash")

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
                st.markdown(response.text or "⚠️ No response from AI.")
    else:
        st.info("Please provide resume content by uploading or entering manually.")
elif tab == "Skill Gap Analyzer":
    st.title("📊 Skill Gap Analyzer")

    job_role = st.text_input("Enter your target job role (e.g., Data Analyst)")

    if not st.session_state.resume_text:
        st.info("Please upload or enter your resume in the 'Resume Analyzer' tab first.")
    else:
        if st.button("Find Skill Gaps"):
            with st.spinner("Analyzing skill gaps..."):
                prompt = (
                    f"You are a career coach. Based on the resume text below, analyze which skills are "
                    f"missing for the user to qualify for the job role: '{job_role}'.\n\n"
                    f"Resume:\n{st.session_state.resume_text}\n\n"
                    "Provide:\n"
                    "1. Required skills for the job\n"
                    "2. Skills already present\n"
                    "3. Skill gaps\n"
                    "4. How to acquire missing skills"
                )
                response = model.generate_content(prompt)
                st.markdown(response.text or "⚠️ No response from AI.")
elif tab == "Ask 🤖":
    st.title("🤖 Ask Pathfinder Chatbot")
    st.markdown("You can ask anything related to careers, skills, jobs, or education.")

    mic_text = speech_to_text(language='en', start_prompt="🎙️ Speak now", stop_prompt="🛑 Stop")
    text_input = st.text_input("Type your question below:", value=mic_text or "")

    if st.button("Ask"):
        if text_input.strip():
            with st.spinner("Thinking..."):
                response = model.generate_content(text_input)
                st.markdown(response.text or "⚠️ No response from AI.")
        else:
            st.warning("Please ask a question via mic or text.")
elif tab == "Job Search":
    st.title("💼 Job Search")
    st.markdown("Search for jobs by role and location (mock data shown)")

    role = st.text_input("Job Title", placeholder="e.g., Software Engineer")
    location = st.text_input("Location", placeholder="e.g., Delhi")

    if st.button("Search Jobs"):
        if role and location:
            with st.spinner("Searching..."):
                mock_jobs = [
                    {
                        "title": f"{role} Intern at TechNova",
                        "location": location,
                        "link": "https://careers.technova.com"
                    },
                    {
                        "title": f"{role} at CodeCraft Inc",
                        "location": location,
                        "link": "https://jobs.codecraft.com"
                    }
                ]
                st.markdown("### 🔎 Job Listings")
                for job in mock_jobs:
                    st.markdown(f"""
                        🔹 **{job['title']}**  
                        📍 Location: *{job['location']}*  
                        🔗 [Apply Now]({job['link']})
                        ---
                    """)
        else:
            st.warning("Please fill in both the job title and location.")

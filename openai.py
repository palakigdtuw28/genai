# final_pathfinder_app.py

import streamlit as st
import os
import google.generativeai as genai
import pandas as pd
import hashlib
from dotenv import load_dotenv
from docx import Document
import pdfplumber
from io import BytesIO

# --- Load Environment Variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# --- User Authentication Helpers ---
USER_DATA_FILE = "user_data.csv"

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
    if os.path.exists(USER_DATA_FILE):
        df = pd.read_csv(USER_DATA_FILE)
        hashed_pw = hash_password(password)
        user_match = df[(df["Username"] == username) & (df["Password"] == hashed_pw)]
        return not user_match.empty
    return False

def get_user_profile(username):
    if os.path.exists(USER_DATA_FILE):
        df = pd.read_csv(USER_DATA_FILE)
        user = df[df["Username"] == username].iloc[0]
        return user["Full Name"], user["Email"]
    return "", ""

# --- Resume Extraction ---
def extract_resume_text(file):
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return "Unsupported file type"

# --- App Initialization ---
st.set_page_config(page_title="Pathfinder AI", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.show_form = True
    st.session_state.resume_text = ""

# --- Login/Register/Guest ---
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

# --- Main App UI ---
if st.session_state.authenticated:
    st.sidebar.title("Navigation")
    tab = st.sidebar.radio("Go to", ["Resume Analyzer", "Skill Gap Analyzer", "Job Search", "Ask 🤖"])

    st.markdown("""
        <style>
            .sidebar-bottom {
                position: fixed;
                bottom: 20px;
                left: 10px;
                font-size: 16px;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("""
            <div class='sidebar-bottom'>
                <a href='#profile'>👤 Profile</a> &nbsp; | &nbsp;
                <a href='#logout'>🔒 Logout</a>
            </div>
        """, unsafe_allow_html=True)

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

    elif tab == "Job Search":
        st.title("🔍 Job Search")
        st.info("This section will soon include live job search integration.")

    elif tab == "Ask 🤖":
        st.subheader("💬 Ask Pathfinder")
        st.markdown("Ask any career-related or factual question below.")
        query = st.text_input("Your question")
        if st.button("Ask"):
            if query:
                with st.spinner("Thinking..."):
                    response = model.generate_content(query)
                    st.markdown("**Response:**")
                    st.markdown(response.text)

# --- Profile and Logout Handlers ---
st.markdown("""
    <h3 id='profile'></h3>
""", unsafe_allow_html=True)

if st.query_params.get("profile") is not None:
    st.title("👤 Profile")
    name, email = get_user_profile(st.session_state.username)
    st.write(f"**Username:** {st.session_state.username}")
    st.write(f"**Full Name:** {name}")
    st.write(f"**Email:** {email}")

st.markdown("""
    <h3 id='logout'></h3>
""", unsafe_allow_html=True)

if st.query_params.get("logout") is not None:
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.resume_text = ""
    st.session_state.show_form = True
    st.rerun()
    

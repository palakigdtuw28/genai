import streamlit as st
import hashlib
import os
import pandas as pd
import pdfplumber
from io import BytesIO
from streamlit_mic_recorder import speech_to_text
import google.generativeai as genai

# ========== Constants ==========
USERS_FILE = "users.csv"

# ========== Initialize User CSV ==========
if not os.path.exists(USERS_FILE):
    df = pd.DataFrame(columns=["username", "email", "password_hash"])
    df.to_csv(USERS_FILE, index=False)

# ========== Helper Functions ==========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(email, password):
    users = pd.read_csv(USERS_FILE)
    hashed = hash_password(password)
    user = users[(users["email"] == email) & (users["password_hash"] == hashed)]
    return user.iloc[0] if not user.empty else None

def register_user(username, email, password):
    users = pd.read_csv(USERS_FILE)
    if email in users["email"].values:
        return False  # Already registered
    new_user = pd.DataFrame([[username, email, hash_password(password)]],
                            columns=["username", "email", "password_hash"])
    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv(USERS_FILE, index=False)
    return True

def clear_session():
    st.session_state.clear()
    st.success("Logged out successfully.")
    st.experimental_rerun()

# ========== Auth UI ==========
def login_register_ui():
    tab = st.radio("🔐 Pathfinder Login / Register", ["Login", "Register", "Guest"], horizontal=True)

    if tab == "Login":
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            user = login_user(email, password)
            if user is not None:
                st.session_state.logged_in = True
                st.session_state.username = user["username"]
                st.session_state.email = email
                st.success(f"✅ Welcome, {user['username']}!")
                st.experimental_rerun()
            else:
                st.error("❌ Invalid email or password.")

    elif tab == "Register":
        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Register"):
            if register_user(username, email, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.email = email
                st.success(f"🎉 Registered and logged in as {username}")
                st.experimental_rerun()
            else:
                st.warning("⚠️ Email already registered.")

    elif tab == "Guest":
        if st.button("Continue as Guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.session_state.email = "guest@pathfinder.ai"
            st.success("🟢 Logged in as Guest")
            st.experimental_rerun()

# ========== Resume Analyzer ==========
def extract_text_from_pdf(uploaded_file):
    with pdfplumber.open(uploaded_file) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def resume_analysis():
    st.subheader("📄 Resume Analyzer")
    option = st.radio("How would you like to provide your resume?", ["Upload PDF", "Enter Manually"])

    if option == "Upload PDF":
        uploaded_file = st.file_uploader("Upload Resume PDF", type="pdf")
        if uploaded_file:
            text = extract_text_from_pdf(BytesIO(uploaded_file.read()))
            st.session_state.resume_text = text
            st.success("Resume parsed successfully.")
            st.text_area("📄 Parsed Resume Text", value=text, height=300)

    elif option == "Enter Manually":
        manual_input = st.text_area("✍️ Paste or write your resume content here")
        if st.button("Save Manual Resume"):
            if manual_input.strip():
                st.session_state.resume_text = manual_input
                st.success("Manual resume saved.")
            else:
                st.warning("Please enter some text.")

    if "resume_text" in st.session_state:
        resume_text = st.session_state.resume_text
        keywords = [word.strip().lower() for word in resume_text.split() if len(word) > 3]
        st.session_state.extracted_skills = list(set(keywords))[:30]

        if st.session_state.extracted_skills:
            st.markdown("### 🧠 Extracted Skills:")
            st.write(", ".join(st.session_state.extracted_skills))

# ========== Skill Gap Analyzer ==========
def skill_gap_analyzer():
    st.subheader("📊 Skill Gap Analyzer")
    if "extracted_skills" not in st.session_state:
        st.warning("⚠️ Please upload or enter your resume first.")
        return

    resume_skills = set(st.session_state.extracted_skills)

    job_roles = {
        "Data Scientist": {"python", "statistics", "sql", "machine learning", "pandas", "numpy"},
        "Web Developer": {"html", "css", "javascript", "react", "node.js", "database"},
        "AI Engineer": {"deep learning", "tensorflow", "python", "nlp", "pytorch"},
        "Cybersecurity Analyst": {"networking", "linux", "firewall", "encryption", "malware"},
    }

    selected_role = st.selectbox("Select Job Role:", list(job_roles.keys()))

    if st.button("🔍 Analyze Skill Gap"):
        required = job_roles[selected_role]
        present = resume_skills
        missing = required - present
        match = required & present

        st.markdown("### ✅ Skills You Have:")
        st.success(", ".join(match) if match else "No matches found.")
        st.markdown("### ❌ Skills You Lack:")
        st.error(", ".join(missing) if missing else "No missing skills. You're all set!")

# ========== Job Search ==========
def job_search():
    st.subheader("🔍 Job Search")
    if "extracted_skills" not in st.session_state:
        st.warning("⚠️ Resume not analyzed yet.")
        return

    user_skills = set(st.session_state.extracted_skills)

    job_listings = [
        {"title": "Data Scientist", "company": "TechCorp", "skills": {"python", "sql", "statistics"}},
        {"title": "Frontend Developer", "company": "Webify", "skills": {"html", "css", "react", "javascript"}},
        {"title": "AI Engineer", "company": "NeuroNet", "skills": {"deep learning", "pytorch", "tensorflow"}},
        {"title": "Cybersecurity Analyst", "company": "SecureShield", "skills": {"firewall", "linux", "networking"}},
    ]

    st.markdown("### 🧠 Based on Your Skills:")
    match_found = False
    for job in job_listings:
        match_score = len(user_skills & job["skills"])
        if match_score > 0:
            match_found = True
            st.markdown(f"**💼 {job['title']}** at *{job['company']}*")
            st.markdown(f"**Required Skills:** {', '.join(job['skills'])}")
            st.markdown(f"**Skill Match:** {match_score} skill(s)")
            st.markdown("---")

    if not match_found:
        st.warning("No matching jobs found. Try improving your skills.")

# ========== Ask Pathfinder ==========
def ask_pathfinder():
    st.subheader("🤖 Ask Pathfinder")
    st.markdown("🎙️ Speak or type your query below:")
    text_input = speech_to_text(language='en', use_container_width=True, just_once=True)
    if not text_input:
        text_input = st.text_input("Or type your question:")

    if text_input:
        with st.spinner("Thinking..."):
            try:
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(text_input)
                st.markdown("### 💬 Response:")
                st.write(response.text)
            except Exception as e:
                st.error("❌ Error generating response.")
                st.exception(e)

# ========== Main App ==========
def main_app():
    with st.sidebar:
        st.markdown("## 🌟 Pathfinder")
        st.markdown("{st.session_state.username}")
        st.markdown("---")
        nav_choice = st.radio("📌 PATHS ", [
            "🏠 Home", "📄 Resume Analysis", "📊 Skill Gap Analyzer",
            "🔍 Job Search", "🤖 Ask Pathfinder"
        ])
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.button("👤 Profile", use_container_width=True)
        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                clear_session()

    if nav_choice == "🏠 Home":
        st.title("👋 Welcome to Pathfinder")
        st.write("Use the sidebar to explore the features.")
    elif nav_choice == "📄 Resume Analysis":
        resume_analysis()
    elif nav_choice == "📊 Skill Gap Analyzer":
        skill_gap_analyzer()
    elif nav_choice == "🔍 Job Search":
        job_search()
    elif nav_choice == "🤖 Ask Pathfinder":
        ask_pathfinder()

# ========== Launch ==========
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    login_register_ui()
else:
    main_app()
        

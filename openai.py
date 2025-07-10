import streamlit as st
import google.generativeai as genai
import os
import requests
import pandas as pd
import hashlib
from dotenv import load_dotenv
from docx import Document
import pdfplumber
from io import BytesIO
from streamlit_mic_recorder import speech_to_text
import re

# --- Load Environment Variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

# --- Configure Gemini ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Page Config & Sidebar ---
st.set_page_config(page_title="Pathfinder - Career Counsellor", layout="centered")
if "_sidebar" not in st.query_params:
    st.query_params["_sidebar"] = "expanded"

# --- Auth Session State ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"

# --- User Auth Utilities ---
USER_DATA_FILE = "user_data.csv"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\\.[^@]+", email)

def user_exists(username):
    if not os.path.exists(USER_DATA_FILE):
        return False
    df = pd.read_csv(USER_DATA_FILE)
    return username in df["Username"].values

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

# --- Sidebar Login/Register/Guest ---
with st.sidebar:
    st.title("🔐 User Access")
    st.session_state.auth_mode = st.radio("Choose Mode", ["Login", "Register", "Guest"])

    if st.session_state.auth_mode == "Register":
        st.subheader("📝 Register")
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        username = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        confirm_pw = st.text_input("Confirm Password", type="password")

        if st.button("Register"):
            if not is_valid_email(email):
                st.warning("⚠ Please enter a valid email.")
            elif user_exists(username):
                st.warning("⚠ Username already exists.")
            elif pw != confirm_pw:
                st.warning("⚠ Passwords do not match.")
            else:
                save_user(name, email, username, pw)
                st.success("✅ Registered! Please login.")
                st.session_state.auth_mode = "Login"

    elif st.session_state.auth_mode == "Login":
        st.subheader("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if authenticate(username, password):
                st.success("✅ Login successful!")
                st.session_state.authenticated = True
            else:
                st.error("❌ Invalid credentials.")

    else:
        st.session_state.authenticated = True  # Guest access

# --- Authenticated User Access ---
if st.session_state.authenticated:

    # --- UI Styling ---
    st.markdown("""
    <style>
        .main-title {
            font-size: 2.6rem;
            font-weight: 700;
            color: #fff;
            background: linear-gradient(90deg, #6e48aa 0%, #9d50bb 100%);
            padding: 1.2rem 0;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 1.1rem;
        }
        .chat-message {
            background: #fff;
            color: #000;
            border-radius: 10px;
            padding: 1.1rem 1rem;
            margin: 0.8rem 0;
            box-shadow: 0 2px 4px rgba(110, 72, 170, 0.07);
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">🎓 Pathfinder – Career Counsellor</div>', unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#6e48aa;'>Ask questions or upload your resume for analysis.</div>", unsafe_allow_html=True)

    # --- State ---
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = ""

    # --- Resume Extractors ---
    def extract_text_from_docx(file):
        try:
            file_buffer = BytesIO(file.read())
            doc = Document(file_buffer)
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception as e:
            return f"❌ Error: {e}"

    def extract_text_from_pdf(file):
        try:
            with pdfplumber.open(BytesIO(file.read())) as pdf:
                return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        except Exception as e:
            return f"❌ Error: {e}"

    # --- Job Search ---
    def search_jobs(query, location="India"):
        url = f"https://{RAPIDAPI_HOST}/search"
        params = {"query": query, "location": location}
        headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST}
        try:
            res = requests.get(url, headers=headers, params=params)
            jobs = res.json().get("data", [])
            if not jobs:
                return "🔍 No jobs found."
            return "\n\n".join([f"{j['job_title']} at {j['employer_name']}\n📍 {j['job_city']}, {j['job_country']}\n🔗 [Apply Here]({j['job_apply_link']})"
                                    for j in jobs[:5]])
        except Exception as e:
            return f"⚠ Error: {e}"

    # --- Show Chat Messages Above Form with Avatar ---
    for msg in reversed(st.session_state.messages):
        avatar = "OIP.webp" if msg["role"] == "assistant" else None
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(f"<div class='chat-message'>{msg['content']}</div>", unsafe_allow_html=True)


    # --- Input Form (Below Messages) ---
    with st.form("chat_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([5, 1, 2])
        with col1:
            user_text = st.text_input("Ask your career-related question...",
                                      label_visibility="collapsed", placeholder="Type your question...")
        with col2:
            mic_text = speech_to_text(start_prompt="🎤", stop_prompt="⏹", just_once=True, use_container_width=True)
        with col3:
            uploaded_file = st.file_uploader("", type=["pdf", "docx"], label_visibility="collapsed")
        submitted = st.form_submit_button("Send", use_container_width=True)

    # --- Handle Input ---
    user_input = user_text or mic_text
    if submitted and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        DOMAIN_PROMPT = (
            "You are a helpful and knowledgeable career/job/college counselling specialist. "
            "Only respond to career/job/college questions. If a question is outside this domain, politely refuse to answer."
        )
        chat_history = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.messages])
        full_prompt = f"{DOMAIN_PROMPT}\n\n{chat_history}\nUser: {user_input}"

        if any(w in user_input.lower() for w in ["job", "jobs", "openings", "vacancy"]):
            bot_reply = search_jobs(user_input)
        else:
            try:
                response = model.generate_content(full_prompt)
                bot_reply = response.text
            except Exception as e:
                bot_reply = f"⚠ Error generating response: {e}"

        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

    # --- Resume Upload + Analysis ---
    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(uploaded_file)
        else:
            text = "❌ Unsupported file format."
        st.session_state.resume_text = text

        st.text_area("📄 Resume Extract (first 500 chars)", text[:500])

        if "❌" not in text:
            analysis_prompt = f"""
You are a career counselor. Analyze this resume:
{text}
Provide:
1. Summary of profile
2. Key skills
3. Suggested roles
4. Areas of improvement
"""
            res = model.generate_content(analysis_prompt)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
    

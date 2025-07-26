import streamlit as st
import hashlib, os, pandas as pd
import pdfplumber
from io import BytesIO
from streamlit_mic_recorder import speech_to_text
import google.generativeai as genai
from dotenv import load_dotenv

# --- Gemini Init ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.0-flash")

# --- User DB Setup ---
USERS_FILE = "users.csv"
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["username","email","password_hash"]).to_csv(USERS_FILE, index=False)

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()
def load_users(): return pd.read_csv(USERS_FILE)

def register_user(username,email,password):
    users = load_users()
    if email in users["email"].values:
        return False
    users = users.append({"username":username,"email":email,"password_hash":hash_pw(password)},ignore_index=True)
    users.to_csv(USERS_FILE,index=False)
    return True

def login_user(email,password):
    users = load_users()
    row = users[(users.email==email)&(users.password_hash==hash_pw(password))]
    return row.iloc[0] if not row.empty else None

# --- Auth UI ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

def show_auth():
    tab = st.radio("Login / Register / Guest", ["Login","Register","Guest"], horizontal=True)
    if tab=="Login":
        email = st.text_input("Email",key="li_email"); pwd = st.text_input("Password",type="password",key="li_pwd")
        if st.button("Login"):
            u = login_user(email,pwd)
            if u is not None:
                st.session_state.logged_in = True
                st.session_state.username = u.username
                st.success(f"Welcome, {u.username}!")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
    elif tab=="Register":
        uname = st.text_input("Username", key="reg_uname")
        email = st.text_input("Email", key="reg_email")
        pwd = st.text_input("Password", type="password", key="reg_pwd")
        if st.button("Register"):
            if register_user(uname,email,pwd):
                st.success("Registered! Please switch to Login tab.")
            else:
                st.warning("Email already exists.")
    else:
        if st.button("Continue as Guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.success("Logged in as Guest")
            st.experimental_rerun()

if not st.session_state.logged_in:
    show_auth()
    st.stop()

# --- Logout ---
def logout():
    st.session_state.clear()
    st.experimental_rerun()

# --- Sidebar Navigation ---
with st.sidebar:
    st.title("🧭 Pathfinder")
    st.write(f"👤 {st.session_state.username}")
    choice = st.radio("Navigate", ["Home","Resume Analyzer","Skill Gap","Job Search","Ask AI"], key="nav")
    if st.button("🔓 Logout"):
        logout()

# --- Feature Functions ---
def resume_analyzer():
    st.header("Resume Analyzer")
    mode = st.radio("Input mode", ["Upload PDF","Write Manually"])
    if mode=="Upload PDF":
        f = st.file_uploader("Upload PDF", type="pdf")
        if f:
            txt = "\n".join(p.extract_text() or "" for p in pdfplumber.open(f).pages)
            st.session_state.resume_text = txt
            st.text_area("Parsed Resume",txt,height=300)
    else:
        txt = st.text_area("Enter resume text")
        if st.button("Save"):
            st.session_state.resume_text = txt
    # extract simple keywords
    if st.session_state.get("resume_text"):
        kws = set(w.lower() for w in st.session_state.resume_text.split() if len(w)>3) 
        st.session_state.resume_skills = list(kws)[:30]
        st.write("Skills:",", ".join(st.session_state.resume_skills))

def skill_gap():
    st.header("Skill Gap Analyzer")
    if "resume_skills" not in st.session_state:
        st.warning("Provide resume first")
        return
    role = st.text_input("Target Role")
    if st.button("Analyze"):
        req = {"python","sql","machine learning","statistics"}  # sample
        present = set(st.session_state.resume_skills)
        st.write("Present:", present & req)
        st.write("Missing:", req - present)

def job_search():
    st.header("Job Search")
    if "resume_skills" not in st.session_state:
        st.warning("Provide resume first")
        return
    # simple mock results
    jobs = [
        {"title":"Data Scientist","skills":{"python","sql"}},
        {"title":"AI Engineer","skills":{"python","machine learning","tensorflow"}},
    ]
    for job in jobs:
        score = len(job["skills"] & set(st.session_state.resume_skills))
        if score>0:
            st.write(f"{job['title']} ({score} match)")

def ask_ai():
    st.header("Ask Pathfinder AI")
    t = speech_to_text(language="en", use_container_width=True, just_once=True)
    inp = st.text_input("Or type here:", value=t or "")
    if st.button("Ask"):
        if inp:
            resp = model.generate_content(inp)
            st.write(resp.text)

# --- Main Rendering ---
if choice=="Home":
    st.write("Welcome to Pathfinder. Use sidebar to explore.")
elif choice=="Resume Analyzer":
    resume_analyzer()
elif choice=="Skill Gap":
    skill_gap()
elif choice=="Job Search":
    job_search()
elif choice=="Ask AI":
    ask_ai()


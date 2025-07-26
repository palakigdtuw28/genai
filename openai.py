import streamlit as st
import google.generativeai as genai
import os
import requests
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# --- Session State Initialization ---
if "users" not in st.session_state:
    st.session_state.users = {}  # Format: {username: hashed_password}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Password Hashing Function ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Sidebar Authentication UI ---
with st.sidebar:
    st.title("🔐 Pathfinder Login")

    menu = st.radio("Choose Action", ["Login", "Register", "Guest", "Logout"])

    if menu == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            hashed_input = hash_password(password)
            if username in st.session_state.users and st.session_state.users[username] == hashed_input:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"✅ Welcome back, {username}!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

    elif menu == "Register":
        new_username = st.text_input("Create Username")
        new_password = st.text_input("Create Password", type="password")
        if st.button("Register"):
            if new_username in st.session_state.users:
                st.warning("⚠️ Username already exists.")
            else:
                st.session_state.users[new_username] = hash_password(new_password)
                st.success("✅ Registration successful! Please login.")
                st.rerun()

    elif menu == "Guest":
        if st.button("Enter as Guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.success("✅ Guest mode activated.")
            st.rerun()

    elif menu == "Logout":
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.chat_history.clear()
            st.success("✅ You have been logged out.")
            st.rerun()

# --- Main App Content ---
st.title("🧭 Pathfinder AI Career Assistant")

if not st.session_state.logged_in:
    st.warning("🚪 Please login or use guest mode to continue.")
    st.stop()

st.markdown(f"👋 Hello, **{st.session_state.username}**!")

# ------------------------------
# Chatbot Section
# ------------------------------
st.subheader("🤖 Ask AI Anything (Chatbot)")

user_message = st.chat_input("Type your question here...")

# Display chat history (latest on top)
for chat in reversed(st.session_state.chat_history):
    with st.chat_message(chat["role"]):
        st.markdown(chat["content"])

# Process chatbot input
if user_message:
    st.session_state.chat_history.append({"role": "user", "content": user_message})
    with st.chat_message("assistant"):
        try:
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(user_message)
            ai_reply = response.text
        except Exception as e:
            ai_reply = f"❌ Error: {str(e)}"
        st.markdown(ai_reply)
        st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})

# ------------------------------
# Job Search Section
# ------------------------------
st.subheader("🔍 Job Search")

search_query = st.text_input("Enter job title & location (e.g. 'Software Engineer in Delhi')")

if st.button("Search Jobs"):
    if not RAPIDAPI_KEY:
        st.error("❌ RAPIDAPI_KEY not configured.")
    else:
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        params = {"query": search_query, "page": "1", "num_pages": "1"}

        try:
            response = requests.get("https://jsearch.p.rapidapi.com/search", headers=headers, params=params)
            if response.status_code == 200:
                jobs = response.json().get("data", [])
                if not jobs:
                    st.info("😕 No jobs found. Try a different query.")
                for job in jobs:
                    st.markdown(f"### 💼 {job['job_title']}")
                    st.markdown(f"**Company:** {job['employer_name']}")
                    st.markdown(f"📍 Location: {job['job_city']}, {job['job_country']}")
                    st.markdown(f"🔗 [Apply Here]({job['job_apply_link']})")
                    st.markdown("---")
            else:
                st.error(f"❌ Job API error: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Failed to fetch jobs: {e}")

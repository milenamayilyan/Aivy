!pip install streamlit pyngrok firebase-admin openai

%%writefile aivy_app.py
import streamlit as st
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import re
from firebase_admin import exceptions as firebase_exceptions

# 🛂 Ngrok tunnel URL handling
if "public_url" not in st.session_state:
    st.session_state.public_url = os.getenv("PUBLIC_URL", "http://localhost:8501")

# 🔑 OpenAI Client setup
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

# 🔥 Firebase setup
if not firebase_admin._apps:
    cred = credentials.Certificate("/content/firebase_credentials.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 🛂 Firebase Authentication
def is_valid_email(email):
    # Very basic email validation using regex
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(email_regex, email) is not None

def signup_user(email, password):
    if not is_valid_email(email):
        st.error("⚠️ Please enter a valid email address.")
        return
    if len(password) < 6:
        st.error("⚠️ Password must be at least 6 characters long.")
        return

    try:
        auth.create_user(email=email, password=password)
        st.success("✅ Account created! Please log in.")
    except firebase_exceptions.AlreadyExistsError:
        st.error("⚠️ This email is already in use. Please log in instead.")
    except firebase_exceptions.InvalidArgumentError:
        st.error("⚠️ Invalid email or password format.")
    except Exception as e:
        st.error(f"⚠️ Signup failed: {e}")

def login_user(email, password):
    try:
        user = auth.get_user_by_email(email)
        return user
    except:
        st.error("Login failed. Please check your credentials.")
        return None

# 🤖 Generate AI response
def generate_reply(user_input):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful AI study assistant."},
            {"role": "user", "content": user_input}
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

# 🛠️ Initialize Session State
for key, default in [("user", None), ("guest", False), ("subjects", ["General"])]:
    if key not in st.session_state:
        st.session_state[key] = default
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {s: [] for s in st.session_state.subjects}

# 📚 Streamlit App Frontend
st.set_page_config(page_title="Aivy - AI Study Assistant", layout="wide", page_icon="📚")

st.markdown("""
    <style>
        .block-container { padding: 2rem 2rem 10rem; }
        .chat-box { background-color: #f0f2f6; padding: 1rem; border-radius: 1rem; margin-bottom: 1rem; }
        .user-msg { background-color: #e0e0e0; border-radius: 1rem; padding: 0.75rem; margin: 0.25rem 0; }
        .aivy-msg { background-color: #dbeafe; border-radius: 1rem; padding: 0.75rem; margin: 0.25rem 0; }
        .fixed-chat-input {
            position: fixed; bottom: 1rem; left: 2rem; right: 2rem;
            background: white; padding: 1rem; box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
            z-index: 999;
        }
    </style>
""", unsafe_allow_html=True)

# 🛂 Login / Signup page
if st.session_state.user is None:
    st.title("📚 Welcome to Aivy")
    st.subheader("Login or Sign Up")

    option = st.radio("Choose an option", ("Login", "Sign Up", "Continue as Guest"))
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if option == "Login" and st.button("Log In"):
        user = login_user(email, password)
        if user:
            st.session_state.user = user
            st.session_state.guest = False
            st.rerun()

    elif option == "Sign Up" and st.button("Sign Up"):
        signup_user(email, password)

    elif option == "Continue as Guest" and st.button("Enter as Guest"):
        st.session_state.user = "guest"
        st.session_state.guest = True
        st.rerun()

# 🚀 Main App after login
if st.session_state.user is not None:
    if st.session_state.guest:
        st.warning("You are using Aivy in guest mode. Your chat history won't be saved permanently.")

    with st.sidebar:
        st.title("📁 Subjects")
        selected_subject = st.radio("Select Subject", st.session_state.subjects)
        new_subject = st.text_input("New Subject")
        if st.button("Add Subject") and new_subject and new_subject not in st.session_state.subjects:
            st.session_state.subjects.append(new_subject)
            st.session_state.chat_history[new_subject] = []
            st.rerun()
        if st.button("Log out"):
            st.session_state.user = None
            st.rerun()

    st.title(f"📚 Aivy - {selected_subject} Chat")

    for entry in st.session_state.chat_history[selected_subject]:
        role_class = "user-msg" if entry["role"] == "user" else "aivy-msg"
        st.markdown(f"<div class='{role_class}'>{entry['text']}</div>", unsafe_allow_html=True)

# 📥 Chat Input Section (Cleaned and Expanded)
st.markdown('<div class="fixed-chat-input">', unsafe_allow_html=True)
col1, _ = st.columns([10, 0.0001])  # Make input bar wider by reducing second column

with col1:
    user_input = st.chat_input("Ask Aivy something...")  # Chat input bar

st.markdown('</div>', unsafe_allow_html=True)

if user_input:
    st.session_state.chat_history[selected_subject].append({"role": "user", "text": user_input})
    reply = generate_reply(user_input)
    st.session_state.chat_history[selected_subject].append({"role": "aivy", "text": reply})
    st.rerun()

else:
    st.error("Please login first to use Aivy.")

import threading
import time
import subprocess
from pyngrok import ngrok

# Ngrok authentication
ngrok.set_auth_token("YOUR_NGROK_AUTHTOKEN")

# Function to run Streamlit app
def run():
    subprocess.run(["streamlit", "run", "aivy_app.py", "--server.port", "8501", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"])

# Start Streamlit app in a separate thread
thread = threading.Thread(target=run)
thread.start()

# Wait for the app to start
time.sleep(5)

# Create ngrok tunnel
try:
    # Use `addr` instead of `port`
    public_url = ngrok.connect(addr="8501", proto="http")
    print(f"🌐 Your app is live at: {public_url}")
except Exception as e:
    print(f"Error starting ngrok tunnel: {e}")

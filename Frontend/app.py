import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/chat/"

st.set_page_config(page_title="AI Assistant", page_icon="🧠", layout="centered")

# --- Initialize session state ---
if "history" not in st.session_state:
    st.session_state.history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# --- Header ---
st.markdown("""
    <h1 style="text-align:center; color:#4B8BBE;">🧠 AI Calender Assistant</h1>
    <p style="text-align:center; color:gray;">Talk to your assistant  with ease.</p>
    <hr>
""", unsafe_allow_html=True)

# --- Display Chat Messages ---
chat_container = st.container()
with chat_container:
    for sender, message in st.session_state.history:
        if sender == "You":
            st.markdown(f"""
            <div style="background-color:#DCF8C6; padding:10px 15px; border-radius:10px; margin:5px 0; max-width:80%; align-self:flex-end;">
                <strong style="color:#2A7B2E;">🧑 {sender}:</strong><br><span style="color:#1A4D1A;">{message}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background-color:#F1F0F0; padding:10px 15px; border-radius:10px; margin:5px 0; max-width:80%; align-self:flex-start;">
                <strong style="color:#2A7B2E;">🤖 {sender}:</strong><br><span style="color:#1A4D1A;">{message}</span>
            </div>
            """, unsafe_allow_html=True)

# --- Spacer to push input down ---
st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)

# --- Input and Submit ---
def handle_input():
    user_input = st.session_state.user_input.strip()
    if not user_input:
        return

    payload = {
        "message": user_input,
        "session_id": "default"
    }

    try:
        response = requests.post(API_URL, json=payload)
        if response.headers.get("Content-Type", "").startswith("application/json"):
            data = response.json()
            assistant_reply = data.get("response", "[No reply]")
        else:
            assistant_reply = f"[⚠️ Warning] Response is not JSON:\n{response.text}"

    except requests.exceptions.RequestException as e:
        assistant_reply = f"[❌ Request Error]: {e}"
    except Exception as e:
        assistant_reply = f"[❌ Unexpected Error]: {e}"

    # Update chat history
    st.session_state.history.append(("You", user_input))
    st.session_state.history.append(("Assistant", assistant_reply))

    # Clear input after sending
    st.session_state.user_input = ""

# --- Text Input ---
st.text_input("Type your message:", key="user_input", on_change=handle_input, label_visibility="collapsed")

# --- Footer ---
st.markdown("""
    <hr>
    <p style='text-align:center; color:gray; font-size:12px;'>Built by Prachi using FastAPI, Gemini & Streamlit</p>
""", unsafe_allow_html=True)

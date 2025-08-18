#!/usr/bin/env python3
import os
import json
import hashlib
import requests
import pandas as pd
import streamlit as st
import subprocess

# === Utilidad para cargar archivo .env ===
def cargar_env(path="/app/backend/.env"):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        lines = f.readlines()
    env = {}
    for line in lines:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v
    return env

# === Page configuration ===
st.set_page_config(
    page_title="Oracle Chatbot",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === Data paths ===
CREDENTIALS_PATH     = "credenciales/usuarios.json"
GENERAL_FEEDBACK_CSV = "feedback/fback.csv"
GENERAL_FEEDBACK_JSON= "feedback/fback.json"
ICON_FEEDBACK_JSON   = "feedback/fback_icon.json"

# === Auth helpers ===
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users() -> dict:
    if os.path.exists(CREDENTIALS_PATH):
        return json.load(open(CREDENTIALS_PATH))
    return {}

def save_users(users: dict):
    os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
    json.dump(users, open(CREDENTIALS_PATH, "w"), indent=2)

# Ensure default admin exists
users = load_users()
if "admin" not in users:
    users["admin"] = hash_password("admin")
    save_users(users)

# === Authentication flow ===
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.sidebar.header("🔐 Login")
    username_input = st.sidebar.text_input("Username")
    password_input = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Log In"):
        users = load_users()
        if username_input in users and users[username_input] == hash_password(password_input):
            st.session_state.authenticated = True
            st.session_state.username = username_input
        else:
            st.sidebar.error("Invalid username or password.")
    st.stop()

# === Sidebar: General feedback ===
st.sidebar.header("📝 General Feedback")
fb_text = st.sidebar.text_area("What would you improve?", height=120)
if st.sidebar.button("Submit Feedback"):
    if fb_text.strip():
        entry = {
            "username":  st.session_state.username,
            "feedback":  fb_text.strip()
        }
        pd.DataFrame([entry]).to_csv(
            GENERAL_FEEDBACK_CSV,
            mode="a",
            header=not os.path.exists(GENERAL_FEEDBACK_CSV),
            index=False
        )
        arr = json.load(open(GENERAL_FEEDBACK_JSON)) if os.path.exists(GENERAL_FEEDBACK_JSON) else []
        arr.append(entry)
        json.dump(arr, open(GENERAL_FEEDBACK_JSON, "w"), indent=2)
        st.sidebar.success("✅ Thank you for your feedback!")
    else:
        st.sidebar.warning("Please enter feedback before submitting.")

# === Sidebar: Account settings ===
st.sidebar.header("⚙️ Account")
with st.sidebar.expander("Change Password"):
    with st.form("change_password_form"):
        current_pw = st.text_input("Current password", type="password")
        new_pw     = st.text_input("New password", type="password")
        confirm_pw = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Submit"):
            users = load_users()
            uname = st.session_state.username
            if users.get(uname) != hash_password(current_pw):
                st.sidebar.error("Current password is incorrect.")
            elif new_pw != confirm_pw:
                st.sidebar.error("New passwords do not match.")
            else:
                users[uname] = hash_password(new_pw)
                save_users(users)
                st.sidebar.success("Password updated successfully!")

# === FORMULARIO DE CONFIGURACIÓN DE ENTORNO ===
with st.expander("📝 Configure deployment environment (without executing)", expanded=True):
    with st.form("env_form"):
        container = st.text_input("Container name (e.g. dbai9)", max_chars=20)
        port      = st.text_input("External port (e.g. 1529)", max_chars=5)
        pwd       = st.text_input("Oracle password", type="password")
        submitted = st.form_submit_button("Save .env")

        if submitted:
            env_path = "/app/backend/.env"
            volume_path = f"/opt/vector-ai/{container}/volume/source"
            dir_del     = f"/opt/vector-ai/{container}"
            ip          = "10.0.0.3"

            env_content = f"""CONTAINER_NAME={container}
PORT={port}
VOLUME_PATH={volume_path}
ORACLE_PWD={pwd}
DIR_DEL={dir_del}
IP={ip}
"""

            try:
                with open(env_path, "w") as f:
                    f.write(env_content)
                st.success(f".env updated at {env_path}")
                st.code(env_content, language="bash")
            except Exception as e:
                st.error(f"❌ Error writing .env: {e}")

# === CARGAR .env ===
env_vars = cargar_env()

# === UPLOAD PDFS + EMBEDDING ===
with st.expander("📄 Upload PDFs to your Oracle vector database", expanded=False):
    if not env_vars.get("VOLUME_PATH"):
        st.warning("⚠️ Please configure and save the .env file first.")
    else:
        uploaded_files = st.file_uploader(
            "Upload your PDF files to be indexed",
            type=["pdf"],
            accept_multiple_files=True
        )

        if st.button("📥 Upload PDFs"):
            path_destino = env_vars["VOLUME_PATH"]
            os.makedirs(path_destino, exist_ok=True)
            success_files = []
            for file in uploaded_files:
                with open(os.path.join(path_destino, file.name), "wb") as f:
                    f.write(file.read())
                success_files.append(file.name)
            if success_files:
                st.success(f"✅ Uploaded: {', '.join(success_files)}")
            else:
                st.warning("No files uploaded.")

        if st.button("📌 Embed into vector database"):
            try:
                result = subprocess.run(["python3", "/app/backend/trigger_embed.py"], capture_output=True, text=True)
                st.success("✅ Embedding completed")
                st.text_area("📤 Output", result.stdout)
                if result.stderr:
                    st.text_area("⚠️ Errors", result.stderr)
            except Exception as e:
                st.error(f"❌ Error running embedding: {e}")

# === Initialize chat history & metadata ===
if "history" not in st.session_state:
    st.session_state.history = []
if "metadata" not in st.session_state:
    st.session_state.metadata = []
if "feedback_mode" not in st.session_state:
    st.session_state.feedback_mode = {}

# === Main title ===
st.markdown("<h1 style='text-align:center;'>🤖 Oracle Assistant </h1>", unsafe_allow_html=True)

# === Capture user prompt ===
user_prompt = st.chat_input("Type your question here…")
if user_prompt:
    st.session_state.history.append(("user", user_prompt))

    with st.spinner("RODOD / DBE Assistant is thinking…"):
        try:
            resp = requests.post(
                "http://localhost:5000/api/v1/chatbot",
                json={"question": user_prompt},
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            resp.raise_for_status()
            payload      = resp.json()
            raw_response = payload.get("response", "")
            try:
                parsed     = json.loads(raw_response)
                bot_answer = parsed.get("answer", raw_response)
                meta_chunks= parsed.get("retrieved_chunks_metadata", [])
            except json.JSONDecodeError:
                bot_answer = raw_response
                meta_chunks= []
        except Exception as e:
            bot_answer = f"❌ Connection error:\n{e}"
            meta_chunks= []

    st.session_state.history.append(("assistant", bot_answer))
    st.session_state.metadata = meta_chunks

# === Render chat bubbles ===
for idx, (role, content) in enumerate(st.session_state.history):
    with st.chat_message(role):
        st.markdown(content)
        if role == "assistant":
            c1, c2, c3 = st.columns([8,1,1], gap="small")
            with c2:
                if st.button("👍", key=f"like_{idx}"):
                    st.session_state.feedback_mode[idx] = "like"
            with c3:
                if st.button("👎", key=f"dislike_{idx}"):
                    st.session_state.feedback_mode[idx] = "dislike"

            if idx in st.session_state.feedback_mode:
                choice = st.session_state.feedback_mode[idx]
                st.markdown(f"**You selected:** {choice.upper()}")
                cmnt = st.text_area("Leave your comment:", key=f"comment_{idx}")
                if st.button("Submit this feedback", key=f"submit_fb_{idx}"):
                    q = ""
                    if idx > 0 and st.session_state.history[idx-1][0] == "user":
                        q = st.session_state.history[idx-1][1]
                    record = {
                        "username":  st.session_state.username,
                        "question":  q,
                        "answer":    content,
                        "icon":      choice,
                        "feedback":  cmnt.strip()
                    }
                    arr = json.load(open(ICON_FEEDBACK_JSON)) if os.path.exists(ICON_FEEDBACK_JSON) else []
                    arr.append(record)
                    os.makedirs(os.path.dirname(ICON_FEEDBACK_JSON), exist_ok=True)
                    json.dump(arr, open(ICON_FEEDBACK_JSON, "w"), indent=2, ensure_ascii=False)
                    st.success("✅ Your feedback has been recorded!")
                    del st.session_state.feedback_mode[idx]

# === Display retrieved-chunk metadata in expandable section ===
if st.session_state.metadata:
    st.markdown("---")
    with st.expander("📑 PDF Source (click to expand)", expanded=False):
        for chunk in st.session_state.metadata:
            chunk.setdefault("text", "[No content provided]")
        df_meta = pd.DataFrame(st.session_state.metadata)
        st.table(df_meta[["source", "chunk_id", "text"]] if "text" in df_meta.columns else df_meta)
    with st.expander("📄 View raw metadata JSON"):
        st.json(st.session_state.metadata)


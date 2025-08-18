#!/usr/bin/env python3
import os
import json
import hashlib
import requests
import pandas as pd
import streamlit as st
import subprocess
from streamlit_chat import message  # Importamos la librería para mensajes de chat con estilo

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
    initial_sidebar_state="expanded",
    page_icon="🤖"
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
    with st.sidebar:
        st.markdown("## 🔐 Login")
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        if st.button("Log In", key="login_button"):
            users = load_users()
            if username_input in users and users[username_input] == hash_password(password_input):
                st.session_state.authenticated = True
                st.session_state.username = username_input
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop()

# === Sidebar: Account settings ===
with st.sidebar:

    # Model Info
    st.sidebar.markdown(
        """
        <div style='margin-bottom: 10px; padding: 10px; background-color: #f0f2f6; border-radius: 10px; text-align: center;'>
            <div style='font-size: 14px; color: #6c757d;'>Model</div>
            <div style='font-weight: bold; font-size: 16px; color: #343a40;'>openai.gpt-4o</div>
            <div style='font-weight: bold; font-size: 16px; color: #343a40;'>tokens 16000 </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("## ⚙️ Account Settings")
    with st.expander("🔑 Change Password"):
        with st.form("change_password_form"):
            current_pw = st.text_input("Current password", type="password")
            new_pw     = st.text_input("New password", type="password")
            confirm_pw = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Submit"):
                users = load_users()
                uname = st.session_state.username
                if users.get(uname) != hash_password(current_pw):
                    st.error("Current password is incorrect.")
                elif new_pw != confirm_pw:
                    st.error("New passwords do not match.")
                else:
                    users[uname] = hash_password(new_pw)
                    save_users(users)
                    st.success("Password updated successfully!")


    # Feedback Section
    st.markdown("## 📝 Feedback")
    fb_text = st.text_area("What would you improve?", height=100, key="feedback_area")
    if st.button("Submit Feedback", key="feedback_button"):
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
            st.success("✅ Thank you for your feedback!")
        else:
            st.warning("Please enter feedback before submitting.")

# === FORMULARIO DE CONFIGURACIÓN DE ENTORNO ===
with st.expander("📦 VECTOR DATABASE CONFIGURATION", expanded=False):
    with st.form("env_form"):
        container = st.text_input("Container name (e.g. dbai9)", max_chars=20)
        port      = st.text_input("External port (e.g. 1529)", max_chars=5)
        pwd       = st.text_input("Password", type="password")
        submitted = st.form_submit_button("🚀 CREATE DATABASE")

        if submitted:
            # Leer COSTUMER desde archivo
            costumer_file = "/app/marketplace/oracle"
            costumer = "default"
            if os.path.exists(costumer_file):
                with open(costumer_file) as f:
                    for line in f:
                        if line.startswith("COSTUMER="):
                            costumer = line.strip().split("=", 1)[1]
                            break

            env_filename = f".env_{costumer}"
            env_path = f"/app/backend/{env_filename}"

            volume_path = f"/home/opc/moca1/opt/vector-ai/{container}/volume/source"
            dir_del     = f"/home/opc/moca1/opt/vector-ai/{container}"
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

                st.success(f"✅ Parameters updated in:\n{env_path}")
                st.code(env_content, language="bash")

                try:
                    result = subprocess.run(
                        ["/bin/bash", "/app/backend/trigger_db.py"],
                        capture_output=True, text=True, check=True
                    )
                    st.success("✅ Database has been initialized successfully!")
                    with st.expander("View initialization output"):
                        st.text(result.stdout)
                        if result.stderr:
                            st.text("Errors:")
                            st.text(result.stderr)
                except subprocess.CalledProcessError as e:
                    st.error(f"❌ Error running database initialization:\n{e.stderr}")

            except Exception as e:
                st.error(f"❌ Error writing .env: {e}")

# === CARGAR .env dinámicamente desde .env_<COSTUMER> ===
def detectar_costumer():
    costumer_file = "/app/marketplace/oracle"
    if os.path.exists(costumer_file):
        with open(costumer_file) as f:
            for line in f:
                if line.startswith("COSTUMER="):
                    return line.strip().split("=", 1)[1]
    return "default"

costumer = detectar_costumer()
env_path = f"/app/backend/.env_{costumer}"
env_vars = cargar_env(env_path)

# === UPLOAD PDFS + EMBEDDING + DELETE DB ===
with st.expander("📄 UPLOAD & PROCESS PDFs", expanded=False):
    if not env_vars.get("VOLUME_PATH"):
        st.warning("⚠️ No VOLUME_PATH found in {env_path}")
    else:
        uploaded_files = st.file_uploader(
            "Upload your PDF files to be indexed",
            type=["pdf"],
            accept_multiple_files=True
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📥 Upload PDFs", help="Upload selected PDF files"):
                if uploaded_files:
                    path_destino = env_vars["VOLUME_PATH"]
                    os.makedirs(path_destino, exist_ok=True)
                    success_files = []
                    for file in uploaded_files:
                        with open(os.path.join(path_destino, file.name), "wb") as f:
                            f.write(file.read())
                        success_files.append(file.name)
                    st.success(f"✅ Uploaded {len(success_files)} files: {', '.join(success_files[:3])}{'...' if len(success_files) > 3 else ''}")
                else:
                    st.warning("No files selected for upload.")

        with col2:
            if st.button("🧠 Embed PDFs", help="Process and embed PDFs into vector database"):
                try:
                    with st.spinner("Processing PDFs..."):
                        result = subprocess.run(
                            ["/bin/bash", "/app/backend/trigger_embed.py"],
                            capture_output=True, text=True, check=True
                        )
                    st.success("✅ PDFs embedded successfully!")
                    with st.expander("View processing output"):
                        st.text(result.stdout)
                        if result.stderr:
                            st.text("Errors:")
                            st.text(result.stderr)
                except subprocess.CalledProcessError as e:
                    st.error(f"❌ Error during embedding:\n{e.stderr}")

        with col3:
            if st.button("🗑️ Delete Database", help="Delete the current vector database"):
                try:
                    with st.spinner("Deleting database..."):
                        result = subprocess.run(
                            ["/bin/bash", "/app/backend/delete.sh"],
                            capture_output=True, text=True, check=True
                        )
                    st.success("✅ Database deleted successfully!")
                    with st.expander("View deletion output"):
                        st.text(result.stdout)
                        if result.stderr:
                            st.text("Errors:")
                            st.text(result.stderr)
                except subprocess.CalledProcessError as e:
                    st.error(f"❌ Error during deletion:\n{e.stderr}")

# === Initialize chat history & metadata ===
if "history" not in st.session_state:
    st.session_state.history = []
if "metadata" not in st.session_state:
    st.session_state.metadata = []
if "feedback_mode" not in st.session_state:
    st.session_state.feedback_mode = {}

# === Main title with better styling ===
st.markdown("""
<div style='text-align: center; margin-bottom: 30px;'>
    <h1 style='color: #4e73df;'>🤖 Oracle AI Assistant</h1>
    <p style='color: #858796;'>Ask me anything about your documents!</p>
</div>
""", unsafe_allow_html=True)

# === Chat container with better styling ===
chat_container = st.container()

# === Capture user prompt ===
user_prompt = st.chat_input("Type your question here...", key="chat_input")
if user_prompt:
    st.session_state.history.append(("user", user_prompt))

    with st.spinner("💭 Thinking..."):
        try:
            resp = requests.post(
                "http://localhost:5000/api/v1/chatbot",
                json={"question": user_prompt},
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            resp.raise_for_status()
            payload = resp.json()
            raw_response = payload.get("response", "")
            try:
                parsed = json.loads(raw_response)
                # Extraer ambas respuestas
                context_answer = parsed.get("answer", "No answer from context")
                technical_answer = parsed.get("answer2", "No technical answer")
                meta_chunks = parsed.get("retrieved_chunks_metadata", [])
                
                # Agregar ambas respuestas al historial como mensajes separados
                st.session_state.history.append(("assistant", f"·Well-founded Answer:\n{context_answer}"))
                st.session_state.history.append(("assistant", f"·Free-form Answer:\n{technical_answer}"))
                
            except json.JSONDecodeError:
                bot_answer = raw_response
                meta_chunks = []
        except Exception as e:
            bot_answer = f"❌ Error: {str(e)}"
            meta_chunks = []

    st.session_state.metadata = meta_chunks
    st.rerun()

# === Render chat bubbles with streamlit-chat ===
with chat_container:
    for idx, (role, content) in enumerate(st.session_state.history):
        if role == "user":
            message(content, is_user=True, key=f"user_{idx}",
                   avatar_style="bottts-neutral", seed="Demo9")
        else:
            message(content, key=f"assistant_{idx}",
                   avatar_style="bottts", seed="OracleBot")

            # Feedback buttons with better styling
            cols = st.columns([0.8, 0.1, 0.1])
            with cols[1]:
                if st.button("👍", key=f"like_{idx}", help="This response was helpful"):
                    st.session_state.feedback_mode[idx] = "like"
                    st.rerun()
            with cols[2]:
                if st.button("👎", key=f"dislike_{idx}", help="This response was not helpful"):
                    st.session_state.feedback_mode[idx] = "dislike"
                    st.rerun()

            # Feedback form if button was clicked
            if idx in st.session_state.feedback_mode:
                choice = st.session_state.feedback_mode[idx]
                st.markdown(f"**You selected:** {choice.upper()}")
                cmnt = st.text_area("Leave your comment:", key=f"comment_{idx}")
                if st.button("Submit feedback", key=f"submit_fb_{idx}"):
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
                    st.success("✅ Feedback submitted!")
                    del st.session_state.feedback_mode[idx]
                    st.rerun()

# === Display retrieved-chunk metadata in expandable section ===
if st.session_state.metadata:
    st.markdown("---")
    with st.expander("📚 Source Documents", expanded=False):
        for chunk in st.session_state.metadata:
            chunk.setdefault("text", "[No content provided]")
        df_meta = pd.DataFrame(st.session_state.metadata)
        st.dataframe(df_meta[["source", "chunk_id", "text"]] if "text" in df_meta.columns else df_meta,
                    use_container_width=True, hide_index=True)

    with st.expander("🔍 Raw Metadata", expanded=False):
        st.json(st.session_state.metadata)


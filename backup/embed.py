import os
import sys
import json
import oracledb
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.embeddings import OCIGenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain_community.llms import OCIGenAI
import oci
from flask import Flask, request, jsonify

# ==== Cargar archivo .env personalizado ====
def load_env_vars(env_file=".env"):
    env_vars = {}
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    env_vars[key] = value
    except FileNotFoundError:
        print(f"⚠️ File {env_file} not found")
    except Exception as e:
        print(f"⚠️ Error reading {env_file}: {e}")
    return env_vars

# ==== Leer COSTUMER desde argumento ====
if len(sys.argv) < 2:
    print("❌ Missing COSTUMER argument. Usage: python3 embed.py <COSTUMER>")
    sys.exit(1)

costumer = sys.argv[1]
env_file = f".env_{costumer}"
print(f"📦 Loading environment variables from {env_file}...")

env_vars = load_env_vars(env_file)

# ==== Validar variables necesarias ====
required_vars = ["VOLUME_PATH", "PORT", "CONTAINER_NAME", "ORACLE_PWD", "IP"]
missing_vars = [var for var in required_vars if var not in env_vars]
if missing_vars:
    print(f"❌ Error: Missing variables in {env_file}: {', '.join(missing_vars)}")
    sys.exit(1)

# ==== Asignar variables ====
VOLUME_PATH = env_vars["VOLUME_PATH"]
PORT = env_vars["PORT"]
CONTAINER_NAME = env_vars["CONTAINER_NAME"]
PASS = env_vars["ORACLE_PWD"]
IP = env_vars["IP"]

# ==== CONFIGURACIÓN ====
CONFIG_PROFILE = "DEFAULT"
COMPARTMENT_ID = "ocid1.compartment.oc1..aaaaaaaanb4wwcxt27nwxmwad6ddxckr6f6h7biazhouccnfjfq5acvbjd6q"
VECTOR_TABLE = "MY_DEMO"
FOLDER_PATH = VOLUME_PATH
DSN = f"{IP}:{PORT}/freepdb1"
USER = "sys"
EMBED_MODEL_ID = "cohere.embed-english-v3.0"
LLM_MODEL_ID = "cohere.command-english-v3.0"
ENDPOINT = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"

# ==== CONEXIÓN A ORACLE DB ====
print(f"🔌 Configuring Oracle DB connection on port {PORT}...")
try:
    conn = oracledb.connect(user=USER, password=PASS, dsn=DSN, mode=oracledb.AUTH_MODE_SYSDBA)
    print("✅ Oracle DB connection successful")
except Exception as e:
    print("❌ Connection error:", e)
    sys.exit(1)

# ========== CONFIG ==========
CONFIG_PROFILE = "DEFAULT"
COMPARTMENT_ID = "ocid1.compartment.oc1..aaaaaaaanb4wwcxt27nwxmwad6ddxckr6f6h7biazhouccnfjfq5acvbjd6q"
VECTOR_TABLE = "MY_DEMO"
FOLDER_PATH = VOLUME_PATH
DSN = f"{IP}:{PORT}/freepdb1"  # Dynamic port from .env
USER = "sys"
EMBED_MODEL_ID = "cohere.embed-english-v3.0"
LLM_MODEL_ID = "cohere.command-english-v3.0"
ENDPOINT = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"

# ========== ORACLE CONNECTION ==========
print(f"🔌 Configuring Oracle DB connection on port {PORT}...")

try:
    conn = oracledb.connect(user=USER, password=PASS, dsn=DSN, mode=oracledb.AUTH_MODE_SYSDBA)
    print("✅ Oracle DB connection successful")
except Exception as e:
    print("❌ Connection error:", e)
    exit()

# ========== OCI CONFIG ==========
config = oci.config.from_file("~/.oci/config", CONFIG_PROFILE)

# ========== EMBEDDINGS ==========
pdf_files = [f for f in os.listdir(FOLDER_PATH) if f.endswith(".pdf")]
all_chunks = []

for filename in pdf_files:
    filepath = os.path.join(FOLDER_PATH, filename)
    print(f"📄 Processing file: {filename}")
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    splitter = CharacterTextSplitter(separator=".", chunk_size=2000, chunk_overlap=100)
    chunks = splitter.split_text(text)

    for i, chunk in enumerate(chunks):
        all_chunks.append(Document(
            page_content=chunk,
            metadata={"source": filename, "chunk_id": f"{filename}_chunk_{i}"}
        ))

print("🔖 Chunks generated")

embed_model = OCIGenAIEmbeddings(
    model_id=EMBED_MODEL_ID,
    service_endpoint=ENDPOINT,
    compartment_id=COMPARTMENT_ID
)

print("🚀 Starting embedding and chunk insertion...")
OracleVS.from_documents(
    all_chunks,
    embed_model,
    client=conn,
    table_name=VECTOR_TABLE,
    distance_strategy=DistanceStrategy.DOT_PRODUCT
)

print("✅ Vector store completed and inserted into table MY_DEMO")

# ========== FLASK BACKEND ==========
app = Flask(__name__)

llm = OCIGenAI(
    model_id=LLM_MODEL_ID,
    service_endpoint=ENDPOINT,
    compartment_id=COMPARTMENT_ID
)

qa = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=OracleVS(
        embedding_function=embed_model,
        client=conn,
        table_name=VECTOR_TABLE,
        distance_strategy=DistanceStrategy.DOT_PRODUCT
    ).as_retriever(search_kwargs={"k": 1}),
    return_source_documents=True
)

@app.route("/api/v1/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({"success": False, "error": "Question is empty"}), 400

    result = qa.invoke({"query": question})
    source_doc = result["source_documents"][0]
    source_file = source_doc.metadata.get("source", "unknown")

    return jsonify({
        "success": True,
        "question": question,
        "response": result["result"],
        "source_file": source_file
    })

# Don't run the server automatically — you trigger it manually with curl



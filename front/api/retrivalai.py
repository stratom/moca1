#!/usr/bin/env python3.12
import sys
import json
import os
import glob
import oracledb
import oci

from langchain_community.embeddings import OCIGenAIEmbeddings
from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain.schema import Document

# ----------------------------------------
# 0. Buscar archivo con COSTUMER en marketplace
# ----------------------------------------
def detect_costumer_env():
    try:
        for filepath in glob.glob("/app/marketplace/*"):
            with open(filepath) as f:
                for line in f:
                    if line.startswith("COSTUMER="):
                        value = line.strip().split("=", 1)[1]
                        return value
    except Exception as e:
        print(f"⚠️ Error buscando COSTUMER: {e}")
    return None

costumer = detect_costumer_env()
if not costumer:
    print("❌ No se detectó ningún cliente válido en /app/marketplace/")
    exit(1)

env_file = f"/app/backend/.env_{costumer}"

# ----------------------------------------
# 1. Cargar variables del archivo dinámico
# ----------------------------------------
def load_env_vars(env_file):
    env_vars = {}
    try:
        with open(env_file) as f:
            for line in f:
                if line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value
                    os.environ[key] = value
    except FileNotFoundError:
        print(f"⚠️ File {env_file} not found")
        exit(1)
    except Exception as e:
        print(f"⚠️ Error reading {env_file}: {e}")
        exit(1)
    return env_vars

env_vars = load_env_vars(env_file)

# ----------------------------------------
# 2. Validación básica de variables
# ----------------------------------------
required_vars = ["IP", "PORT", "ORACLE_PWD"]
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"❌ Missing required environment variables: {', '.join(missing)}")
    exit(1)

# ----------------------------------
# 3. Captura la pregunta
# ----------------------------------
if len(sys.argv) > 1:
    user_question = sys.argv[1]
else:
    user_question = "What do I need to know before using the Siebel application for the first time?"

# ----------------------------------
# 4. Conexión a Oracle DB
# ----------------------------------
dsn = f"{os.getenv('IP')}:{os.getenv('PORT')}/freepdb1".upper()
conn23c = oracledb.connect(
    user="sys",
    password=os.getenv("ORACLE_PWD"),
    dsn=dsn,
    mode=oracledb.AUTH_MODE_SYSDBA
)

# ----------------------------------
# 5. Parámetros de OCI para Embeddings
# ----------------------------------
embed_compartment_id = "ocid1.compartment.oc1..aaaaaaaanb4wwcxt27nwxmwad6ddxckr6f6h7biazhouccnfjfq5acvbjd6q"
embed_config = oci.config.from_file('~/.oci/config', "DEFAULT")
embed_endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"

# ----------------------------------
# 6. Inicializa embeddings de OCI
# ----------------------------------
embed_model = OCIGenAIEmbeddings(
    model_id="cohere.embed-english-v3.0",
    service_endpoint=embed_endpoint,
    compartment_id=embed_compartment_id
)

# ----------------------------------
# 7. Vector store y retriever
# ----------------------------------
vs = OracleVS(
    embedding_function=embed_model,
    client=conn23c,
    table_name="MY_DEMO",
    distance_strategy=DistanceStrategy.DOT_PRODUCT
)
retriever = vs.as_retriever(search_type="similarity", search_kwargs={'k': 5})

# ----------------------------------
# 8. Configuración Independiente para LLM
# ----------------------------------
llm_compartment_id = "ocid1.compartment.oc1..aaaaaaaaxibr4amfvjf353m3nwpga7gvcrgpmkou2manorv2htmvjazrbcxa"
llm_config = oci.config.from_file('~/.oci/config2', "DEFAULT")
llm_endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"

# Cliente de inferencia LLM independiente
llm_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config=llm_config,
    service_endpoint=llm_endpoint,
    retry_strategy=oci.retry.NoneRetryStrategy(),
    timeout=(10, 240)
)

def chat_with_oci(prompt_text: str) -> str:
    """Función independiente para interactuar con el LLM"""
    from oci.generative_ai_inference.models import (
        ChatDetails, TextContent, Message,
        GenericChatRequest, OnDemandServingMode, BaseChatRequest
    )

    # Configuración del contenido del mensaje
    content = TextContent()
    content.text = prompt_text

    message = Message()
    message.role = "USER"
    message.content = [content]

    # Configuración de la solicitud de chat
    chat_request = GenericChatRequest()
    chat_request.api_format = BaseChatRequest.API_FORMAT_GENERIC
    chat_request.messages = [message]
    chat_request.max_tokens = 16000
    chat_request.temperature = 1
    chat_request.frequency_penalty = 0
    chat_request.presence_penalty = 0
    chat_request.top_p = 1
    chat_request.top_k = 0

    # Configuración de los detalles del chat
    chat_detail = ChatDetails()
    chat_detail.serving_mode = OnDemandServingMode(
        model_id="ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceya663hlflxfx6kiwn7qjlnpye6n7caii5lnvcpjlwr2s2q"
    )
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = llm_compartment_id

    # Ejecución de la solicitud
    chat_response = llm_client.chat(chat_detail)

    # Procesamiento de la respuesta
    return chat_response.data.chat_response.choices[0].message.content[0].text

# ----------------------------------
# 9. Recuperación de chunks + metadata + texto
# ----------------------------------
docs: list[Document] = retriever.get_relevant_documents(user_question)

# Añadir texto directamente al metadata
for doc in docs:
    doc.metadata["text"] = doc.page_content

# Construir contexto para el modelo
context_text = "\n\n".join(doc.page_content for doc in docs)

# Crear ambos prompts
full_prompt = f"""Answer the question based only on the following context:
{context_text}

Question: {user_question}
"""

engineer_prompt = f"""Act as a professional engineer with formal technical knowledge. 
Answer the following question precisely and technically, based only on your trained knowledge:

Question: {user_question}

Provide:
1. A concise technical explanation
2. Relevant best practices
3. Any important considerations
4. Potential limitations or caveats

Answer in Spanish unless the question is in English.
"""

# Obtener ambas respuestas
answer = chat_with_oci(full_prompt).strip()
answer2 = chat_with_oci(engineer_prompt).strip()

# ----------------------------------
# 10. Salida en formato JSON
# ----------------------------------
output = {
    "question": user_question,
    "answer": answer,
    "answer2": answer2,
    "retrieved_chunks_metadata": [doc.metadata for doc in docs]
}

print(json.dumps(output, ensure_ascii=False, indent=2))

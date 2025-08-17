











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

# ----------------------------------------
# 3. Pregunta del usuario
# ----------------------------------------
user_question = sys.argv[1] if len(sys.argv) > 1 else "What is Oracle PCF?"

# ----------------------------------------
# 4. Conexión a Oracle
# ----------------------------------------
dsn = f"{os.getenv('IP')}:{os.getenv('PORT')}/freepdb1".upper()
conn = oracledb.connect(user="sys", password=os.getenv("ORACLE_PWD"), dsn=dsn, mode=oracledb.AUTH_MODE_SYSDBA)

# ----------------------------------------
# 5. OCI Config y embeddings
# ----------------------------------------
compartment_id = "ocid1.compartment.oc1..aaaaaaaanb4wwcxt27nwxmwad6ddxckr6f6h7biazhouccnfjfq5acvbjd6q"
endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
config = oci.config.from_file("~/.oci/config", "DEFAULT")

embed_model = OCIGenAIEmbeddings(
    model_id="cohere.embed-english-v3.0",
    service_endpoint=endpoint,
    compartment_id=compartment_id
)

vs = OracleVS(
    embedding_function=embed_model,
    client=conn,
    table_name="MY_DEMO",
    distance_strategy=DistanceStrategy.DOT_PRODUCT
)
retriever = vs.as_retriever(search_type="similarity", search_kwargs={'k': 5})

# ----------------------------------------
# 6. Cliente LLM (independiente del bloque 5)
# ----------------------------------------
def chat_with_oci(prompt_text):
    from oci.config import from_file
    from oci.generative_ai_inference import GenerativeAiInferenceClient
    from oci.generative_ai_inference.models import (
        ChatDetails, TextContent, Message,
        GenericChatRequest, OnDemandServingMode, BaseChatRequest
    )

    # Configuración totalmente separada
    config_llm = from_file("~/.oci/config2", "DEFAULT")
    endpoint_llm = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
    compartment_id_llm = "ocid1.compartment.oc1..aaaaaaaaxibr4amfvjf353m3nwpga7gvcrgpmkou2manorv2htmvjazrbcxa"

    generative_ai_client = GenerativeAiInferenceClient(
        config=config_llm,
        service_endpoint=endpoint_llm
    )

    chat_detail = ChatDetails()
    content = TextContent(text=prompt_text)
    message_obj = Message(role="USER", content=[content])
    chat_req = GenericChatRequest(
        api_format=BaseChatRequest.API_FORMAT_GENERIC,
        messages=[message_obj],
        max_tokens=16000,  # ← respeta tu configuración original
        temperature=1,
        frequency_penalty=0,
        presence_penalty=0,
        top_p=1,
        top_k=0
    )
    chat_detail.serving_mode = OnDemandServingMode(
        model_id="ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceya663hlflxfx6kiwn7qjlnpye6n7caii5lnvcpjlwr2s2q"
    )
    chat_detail.chat_request = chat_req
    chat_detail.compartment_id = compartment_id_llm

    resp = generative_ai_client.chat(chat_detail)
    return resp.data.chat_response.choices[0].message.content[0].text

# ----------------------------------------
# 7. Recuperación y prompt híbrido
# ----------------------------------------
docs: list[Document] = retriever.get_relevant_documents(user_question)

for doc in docs:
    doc.metadata["text"] = doc.page_content

context_text = "\n\n".join(doc.page_content for doc in docs if doc.page_content.strip())
retrieved_metadata = [doc.metadata for doc in docs if doc.page_content.strip()]

prompt = f"""You are an intelligent assistant named RODOD.

You will be given a user question and a set of context passages from documents.
Use only the context to answer **if the information is clearly present**.
If the context does not contain enough information to answer the question, then answer using your own general knowledge.
Do not mention whether the information comes from the context or from your general knowledge.
Do not say anything like "There is no information in the context" or Based on the provided context, there is no direct mention.

In either case, provide a well-developed, enriched, and informative answer. 
Include relevant details, explanations, reasoning, and examples when helpful.
Expand and elaborate where appropriate to make the answer as useful as possible.

Context:
{context_text if context_text else "[No context available]"}

Question: {user_question}
Answer:"""

answer = chat_with_oci(prompt).strip()

# ----------------------------------------
# 8. Respuesta JSON
# ----------------------------------------
output = {
    "question": user_question,
    "answer": answer,
    "retrieved_chunks_metadata": retrieved_metadata
}

print(json.dumps(output, ensure_ascii=False, indent=2))




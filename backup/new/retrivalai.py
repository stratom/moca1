#!/usr/bin/env python3.12
# coding: utf-8

import sys
import json
import os
import glob
import oracledb
import oci
from typing import List

from langchain_community.embeddings.base import Embeddings
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
user_question = sys.argv[1] if len(sys.argv) > 1 else "what is The generic service fulfillment scenario?"

# ----------------------------------------
# 4. Conexión a Oracle
# ----------------------------------------
dsn = f"{os.getenv('IP')}:{os.getenv('PORT')}/freepdb1".upper()
conn = oracledb.connect(user="sys", password=os.getenv("ORACLE_PWD"), dsn=dsn, mode=oracledb.AUTH_MODE_SYSDBA)

# ----------------------------------------
# 5. OCI Config y embeddings (embed_text directo)
# ----------------------------------------
CONFIG_PROFILE = "DEFAULT"
config = oci.config.from_file("~/.oci/config", CONFIG_PROFILE)
endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
compartment_id = "ocid1.compartment.oc1..aaaaaaaaxibr4amfvjf353m3nwpga7gvcrgpmkou2manorv2htmvjazrbcxa"

generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config=config,
    service_endpoint=endpoint,
    retry_strategy=oci.retry.NoneRetryStrategy(),
    timeout=(10, 240)
)

class OCIDirectEmbeddings(Embeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embed_text_detail = oci.generative_ai_inference.models.EmbedTextDetails(
            serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                model_id="openai.text-embedding-3-large"
            ),
            inputs=texts,
            truncate="NONE",
            compartment_id=compartment_id
        )
        response = generative_ai_inference_client.embed_text(embed_text_detail)
        return [vec.values for vec in response.data.embeddings]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

embed_model = OCIDirectEmbeddings()

vs = OracleVS(
    embedding_function=embed_model,
    client=conn,
    table_name="MY_DEMO",
    distance_strategy=DistanceStrategy.DOT_PRODUCT
)
retriever = vs.as_retriever(search_type="similarity", search_kwargs={'k': 5})

# ----------------------------------------
# 6. Cliente LLM - formato OpenAI
# ----------------------------------------
from oci.generative_ai_inference.models import (
    ChatDetails, TextContent, Message,
    GenericChatRequest, OnDemandServingMode, BaseChatRequest
)

def chat_with_oci(prompt_text):
    content = TextContent(text=prompt_text)
    message = Message(role="USER", content=[content])

    chat_request = GenericChatRequest(
        api_format=BaseChatRequest.API_FORMAT_OPENAI,
        messages=[message],
        max_tokens=4000,
        temperature=1,
        frequency_penalty=0,
        presence_penalty=0,
        top_p=0.75,
        top_k=0
    )

    chat_detail = ChatDetails(
        compartment_id=compartment_id,
        serving_mode=OnDemandServingMode(
            model_id="ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceya663hlflxfx6kiwn7qjlnpye6n7caii5lnvcpjlwr2s2q"
        ),
        chat_request=chat_request
    )

    try:
        response = generative_ai_inference_client.chat(chat_detail)
        return response.data.choices[0].message.content[0].text.strip()
    except Exception as e:
        return f"⚠️ Error: {e}"

# ----------------------------------------
# 7. Recuperación y respuesta
# ----------------------------------------
docs: list[Document] = retriever.get_relevant_documents(user_question)

for doc in docs:
    doc.metadata["text"] = doc.page_content

context_text = "\n\n".join(doc.page_content for doc in docs)

prompt = f"""Answer the question based only on the following context:
{context_text}

Question: {user_question}
"""

answer = chat_with_oci(prompt).strip()

# ----------------------------------------
# 8. Respuesta JSON
# ----------------------------------------
output = {
    "question": user_question,
    "answer": answer,
    "retrieved_chunks_metadata": [doc.metadata for doc in docs]
}

print(json.dumps(output, ensure_ascii=False, indent=2))


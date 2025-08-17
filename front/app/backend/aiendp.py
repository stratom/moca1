# embed_exp.py
import oci
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import EmbedTextDetails, OnDemandServingMode
from oci.exceptions import ServiceError, ConfigFileNotFound, InvalidConfig

try:
    CONFIG_PROFILE = "DEFAULT"
    COMPARTMENT_ID = "ocid1.compartment.oc1..aaaaaaaadwecxpzeqiqqwkz55qwfk3ya2f6xhvqkqjh7livehpchu2qy2ayq"
    ENDPOINT = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"

    config = oci.config.from_file("~/.oci/config", CONFIG_PROFILE)

    client = GenerativeAiInferenceClient(
        config=config,
        service_endpoint=ENDPOINT,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240)
    )

    prompt = input("Ingresa el texto a embebeer (embedding):\n> ")

    embed_text_detail = EmbedTextDetails(
        inputs=[prompt],
        truncate="NONE",
        compartment_id=COMPARTMENT_ID,
        serving_mode=OnDemandServingMode(model_id="cohere.embed-english-light-v2.0")
    )

    response = client.embed_text(embed_text_detail)

    print("✅ Embedding generado exitosamente:")
    for i, vector in enumerate(response.data.embeddings):
        print(f"\nEmbedding {i+1} ({len(vector)} dimensiones):\n{vector}")

except (ConfigFileNotFound, InvalidConfig) as e:
    print("❌ ERROR de configuración:")
    print(str(e))
except ServiceError as e:
    print("❌ ERROR de servicio:")
    print(f"{e.status}: {e.message}")
except Exception as e:
    print("❌ ERROR inesperado:")
    print(str(e))


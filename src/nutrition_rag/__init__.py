from dotenv import load_dotenv
import os

load_dotenv(override=True)

from nutrition_rag.core.config import Settings

settings = Settings()

if settings.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.cohere_api_key and not os.environ.get("COHERE_API_KEY"):
    os.environ["COHERE_API_KEY"] = settings.cohere_api_key
if settings.voyage_api_key and not os.environ.get("VOYAGE_API_KEY"):
    os.environ["VOYAGE_API_KEY"] = settings.voyage_api_key

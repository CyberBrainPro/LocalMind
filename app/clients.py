import chromadb
from chromadb.config import Settings
from openai import OpenAI

from .settings import CHROMA_DB_DIR, LLM_API_KEY, LLM_BASE_URL


client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
)

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DB_DIR,
    settings=Settings(anonymized_telemetry=False),
)

collection = chroma_client.get_or_create_collection("localmind_default")


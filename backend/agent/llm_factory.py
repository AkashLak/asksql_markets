"""
LLM + Embeddings factory.

Reads LLM_PROVIDER from the environment and returns the correct
(chat_llm, embeddings) pair. Supports "openai" and "ollama".

Switch providers by changing LLM_PROVIDER in .env:
  LLM_PROVIDER=ollama -> free, local, no API key needed
  LLM_PROVIDER=openai -> paid, cloud, requires OPENAI_API_KEY
"""

import os

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

load_dotenv()


def get_llm_and_embeddings() -> tuple[BaseChatModel, Embeddings]:
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings

        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )
        embeddings = OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama, OllamaEmbeddings

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        llm = ChatOllama(
            base_url=base_url,
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            temperature=0,
        )
        embeddings = OllamaEmbeddings(
            base_url=base_url,
            model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {provider!r}. "
            "Set LLM_PROVIDER to 'openai' or 'ollama' in your .env file."
        )

    return llm, embeddings


def get_provider_name() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").lower()

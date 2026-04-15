from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from nutrition_rag.core.config import EmbeddingConfig, Settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]: ...

    @property
    @abstractmethod
    def dimension(self) -> int: ...


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config: EmbeddingConfig):
        from langchain_openai import OpenAIEmbeddings

        self._embeddings = OpenAIEmbeddings(model=config.openai_model)
        self._dimension = 1536 if "3-small" in config.openai_model else 3072

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self._embeddings.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self._embeddings.aembed_query(text)

    @property
    def dimension(self) -> int:
        return self._dimension


class CohereEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config: EmbeddingConfig):
        from langchain_cohere import CohereEmbeddings

        self._embeddings = CohereEmbeddings(model=config.cohere_model)
        self._dimension = 1024

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self._embeddings.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self._embeddings.aembed_query(text)

    @property
    def dimension(self) -> int:
        return self._dimension


class VoyageEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config: EmbeddingConfig):
        from langchain_voyageai import VoyageAIEmbeddings

        self._embeddings = VoyageAIEmbeddings(model=config.voyage_model)
        self._dimension = 1024

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self._embeddings.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self._embeddings.aembed_query(text)

    @property
    def dimension(self) -> int:
        return self._dimension


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, config: EmbeddingConfig):
        from langchain_community.embeddings import HuggingFaceEmbeddings

        model_kwargs: dict[str, Any] = {}
        if config.use_gpu:
            model_kwargs["device"] = "cuda"
        self._embeddings = HuggingFaceEmbeddings(
            model_name=config.sentence_transformer_model,
            model_kwargs=model_kwargs,
        )
        self._dimension = 384 if "mini" in config.sentence_transformer_model.lower() else 768

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)

    @property
    def dimension(self) -> int:
        return self._dimension


PROVIDERS: dict[str, type[EmbeddingProvider]] = {
    "openai": OpenAIEmbeddingProvider,
    "cohere": CohereEmbeddingProvider,
    "voyage": VoyageEmbeddingProvider,
    "sentence-transformers": SentenceTransformerProvider,
}


class EmbeddingRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._providers: dict[str, EmbeddingProvider] = {}

    def get_provider(self, model_name: str | None = None) -> EmbeddingProvider:
        name = model_name or self.settings.embedding.active_model
        if name not in self._providers:
            if name not in PROVIDERS:
                raise ValueError(f"Unknown embedding provider: {name}. Available: {list(PROVIDERS.keys())}")
            self._providers[name] = PROVIDERS[name](self.settings.embedding)
            logger.info("Initialized embedding provider: %s (dim=%d)", name, self._providers[name].dimension)
        return self._providers[name]

    def get_active_provider(self) -> EmbeddingProvider:
        return self.get_provider(self.settings.embedding.active_model)

    def list_available(self) -> list[str]:
        return list(PROVIDERS.keys())

    def clear_cache(self) -> None:
        self._providers.clear()

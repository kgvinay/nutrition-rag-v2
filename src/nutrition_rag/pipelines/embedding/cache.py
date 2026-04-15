from __future__ import annotations

import hashlib
import json
import logging
from datetime import timedelta

from nutrition_rag.core.config import Settings

logger = logging.getLogger(__name__)


class EmbeddingCache:
    def __init__(self, settings: Settings, redis_client=None):
        self.settings = settings
        self._redis = redis_client
        self._ttl = timedelta(days=settings.embedding.cache_ttl_days)
        self._prefix = settings.embedding.cache_key_prefix
        self._local_cache: dict[str, list[float]] = {}

    def _make_key(self, content: str, model: str) -> str:
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{self._prefix}{model}:{content_hash}"

    async def get(self, content: str, model: str) -> list[float] | None:
        key = self._make_key(content, model)
        if self._redis:
            cached = await self._redis.get(key)
            if cached:
                logger.debug("Cache hit: %s", key)
                return json.loads(cached)
        else:
            if key in self._local_cache:
                logger.debug("Local cache hit: %s", key)
                return self._local_cache[key]
        return None

    async def set(self, content: str, model: str, embedding: list[float]) -> None:
        key = self._make_key(content, model)
        if self._redis:
            await self._redis.set(key, json.dumps(embedding), ex=int(self._ttl.total_seconds()))
        else:
            self._local_cache[key] = embedding
        logger.debug("Cached embedding: %s", key)

    async def get_batch(self, contents: list[str], model: str) -> tuple[list[list[float] | None], list[int]]:
        results: list[list[float] | None] = []
        missed_indices: list[int] = []
        for i, content in enumerate(contents):
            cached = await self.get(content, model)
            results.append(cached)
            if cached is None:
                missed_indices.append(i)
        logger.debug("Cache batch: %d hits, %d misses", len(contents) - len(missed_indices), len(missed_indices))
        return results, missed_indices

    async def set_batch(self, contents: list[str], model: str, embeddings: list[list[float]]) -> None:
        for content, embedding in zip(contents, embeddings):
            await self.set(content, model, embedding)

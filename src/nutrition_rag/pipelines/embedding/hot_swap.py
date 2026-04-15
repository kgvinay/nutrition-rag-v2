from __future__ import annotations

import logging
from typing import Any

from nutrition_rag.core.config import Settings
from nutrition_rag.pipelines.embedding.registry import EmbeddingRegistry

logger = logging.getLogger(__name__)


class HotSwapManager:
    def __init__(self, settings: Settings, registry: EmbeddingRegistry):
        self.settings = settings
        self.registry = registry
        self._active_model = settings.embedding.active_model
        self._previous_model: str | None = None

    @property
    def active_model(self) -> str:
        return self._active_model

    def swap_model(self, new_model: str) -> None:
        if new_model not in {"openai", "cohere", "voyage", "sentence-transformers"}:
            raise ValueError(f"Unknown model: {new_model}")
        self._previous_model = self._active_model
        self._active_model = new_model
        self.settings.embedding.active_model = new_model
        logger.info("Hot-swapped embedding model: %s → %s", self._previous_model, new_model)

    def rollback(self) -> None:
        if self._previous_model:
            self._active_model = self._previous_model
            self.settings.embedding.active_model = self._previous_model
            logger.info("Rolled back embedding model to: %s", self._previous_model)
            self._previous_model = None

    def get_provider_for_new_chunks(self) -> Any:
        return self.registry.get_provider(self._active_model)

    def get_provider_for_existing_vectors(self) -> list[Any]:
        providers = [self.registry.get_provider(self._active_model)]
        if self._previous_model:
            try:
                providers.append(self.registry.get_provider(self._previous_model))
            except Exception:
                pass
        return providers

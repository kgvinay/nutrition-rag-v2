from __future__ import annotations

import logging

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import Chunk

logger = logging.getLogger(__name__)


class ContextFilter:
    def __init__(self, settings: Settings):
        self.confidence_threshold = settings.retrieval.confidence_threshold
        self.require_disclaimer = settings.retrieval.require_disclaimer_tag
        self.max_context_tokens = settings.retrieval.max_context_tokens

    def filter_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        filtered = []
        for chunk in chunks:
            if chunk.confidence_score < self.confidence_threshold:
                logger.debug(
                    "Filtered out chunk %s: confidence %.2f < %.2f",
                    chunk.id,
                    chunk.confidence_score,
                    self.confidence_threshold,
                )
                continue
            if self.require_disclaimer and not chunk.has_disclaimer:
                logger.debug("Filtered out chunk %s: missing disclaimer tag", chunk.id)
                continue
            filtered.append(chunk)

        token_count = 0
        context_chunks = []
        for chunk in filtered:
            estimated_tokens = len(chunk.content) // 4
            if token_count + estimated_tokens > self.max_context_tokens:
                logger.debug("Context window limit reached at %d tokens", token_count)
                break
            token_count += estimated_tokens
            context_chunks.append(chunk)

        logger.info(
            "Context filter: %d → %d chunks (confidence ≥ %.2f, %s, %d tokens)",
            len(chunks),
            len(context_chunks),
            self.confidence_threshold,
            "disclaimer required" if self.require_disclaimer else "disclaimer optional",
            token_count,
        )
        return context_chunks

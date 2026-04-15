from __future__ import annotations

import logging
import math

from nutrition_rag.core.models import Chunk

logger = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingValidator:
    def __init__(self, failure_threshold: float = 0.02):
        self.failure_threshold = failure_threshold
        self._golden_set: list[tuple[str, list[float]]] = []

    def set_golden_set(self, golden: list[tuple[str, list[float]]]) -> None:
        self._golden_set = golden
        logger.info("Golden validation set loaded: %d entries", len(golden))

    def validate_batch(self, chunks: list[Chunk]) -> tuple[bool, float]:
        if not self._golden_set or not chunks:
            return True, 0.0

        failures = 0
        total = 0
        for chunk in chunks:
            if not chunk.embedding:
                failures += 1
                total += 1
                continue
            for golden_text, golden_vec in self._golden_set:
                sim = cosine_similarity(chunk.embedding, golden_vec)
                total += 1
                if golden_text.lower() in chunk.content.lower() and sim < 0.7:
                    failures += 1
                elif sim > 0.99 and golden_text.lower() not in chunk.content.lower():
                    failures += 1

        failure_rate = failures / total if total > 0 else 0.0
        passed = failure_rate <= self.failure_threshold
        if not passed:
            logger.error(
                "Embedding quality check FAILED: %.2f%% failure rate (threshold: %.2f%%)",
                failure_rate * 100,
                self.failure_threshold * 100,
            )
        else:
            logger.info("Embedding quality check passed: %.2f%% failure rate", failure_rate * 100)
        return passed, failure_rate

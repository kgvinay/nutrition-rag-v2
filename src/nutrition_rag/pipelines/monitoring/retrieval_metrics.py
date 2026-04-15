from __future__ import annotations

import logging
import math
from typing import Any

from nutrition_rag.core.models import Chunk

logger = logging.getLogger(__name__)


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    return len(top_k & relevant_ids) / len(relevant_ids)


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        if doc_id in relevant_ids:
            dcg += 1.0 / math.log2(i + 2)
    ideal_dcg = 0.0
    for i in range(min(len(relevant_ids), k)):
        ideal_dcg += 1.0 / math.log2(i + 2)
    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


class RetrievalMetrics:
    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._metrics: list[dict[str, Any]] = []

    async def record(
        self,
        query: str,
        retrieved_ids: list[str],
        relevant_ids: set[str] | None = None,
        latency_ms: float = 0.0,
        k: int = 10,
    ) -> dict[str, float]:
        recall = recall_at_k(retrieved_ids, relevant_ids or set(), k) if relevant_ids is not None else -1.0
        ndcg = ndcg_at_k(retrieved_ids, relevant_ids or set(), k) if relevant_ids is not None else -1.0
        metrics = {
            "recall_at_k": recall,
            "ndcg_at_k": ndcg,
            "latency_ms": latency_ms,
            "num_retrieved": len(retrieved_ids),
        }
        if self._redis:
            import json

            await self._redis.rpush("metrics:retrieval", json.dumps(metrics))
        else:
            self._metrics.append(metrics)
        logger.info("Retrieval metrics: recall@%d=%.3f, ndcg@%d=%.3f, latency=%.0fms", k, recall, k, ndcg, latency_ms)
        return metrics

    async def get_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        if self._redis:
            import json

            items = await self._redis.lrange("metrics:retrieval", -limit, -1)
            return [json.loads(item) for item in items]
        return self._metrics[-limit:]

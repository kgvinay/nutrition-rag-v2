from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class BusinessMetrics:
    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._metrics: dict[str, Any] = {
            "thumbs_up": 0,
            "thumbs_down": 0,
            "query_volume": 0,
        }

    async def record_feedback(self, positive: bool) -> None:
        key = "thumbs_up" if positive else "thumbs_down"
        if self._redis:
            await self._redis.incr(f"metrics:business:{key}")
        else:
            self._metrics[key] += 1

    async def record_query(self) -> None:
        if self._redis:
            await self._redis.incr("metrics:business:query_volume")
        else:
            self._metrics["query_volume"] += 1

    async def get_metrics(self) -> dict[str, Any]:
        if self._redis:
            thumbs_up = int(await self._redis.get("metrics:business:thumbs_up") or 0)
            thumbs_down = int(await self._redis.get("metrics:business:thumbs_down") or 0)
            query_volume = int(await self._redis.get("metrics:business:query_volume") or 0)
            return {"thumbs_up": thumbs_up, "thumbs_down": thumbs_down, "query_volume": query_volume}
        return self._metrics.copy()

    async def get_satisfaction_rate(self) -> float:
        metrics = await self.get_metrics()
        total = metrics["thumbs_up"] + metrics["thumbs_down"]
        if total == 0:
            return 0.0
        return metrics["thumbs_up"] / total

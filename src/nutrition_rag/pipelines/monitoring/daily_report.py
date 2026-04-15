from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from nutrition_rag.core.config import Settings

logger = logging.getLogger(__name__)


class DailyReportGenerator:
    def __init__(self, settings: Settings, redis_client=None):
        self.settings = settings
        self._redis = redis_client
        self._reports: list[dict[str, Any]] = []

    async def generate_report(self) -> dict[str, Any]:
        retrieval_metrics = await self._get_metrics("metrics:retrieval")
        generation_metrics = await self._get_metrics("metrics:generation")
        report = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "generated_at": datetime.utcnow().isoformat(),
            "summary": self._summarize(retrieval_metrics, generation_metrics),
            "retrieval": retrieval_metrics,
            "generation": generation_metrics,
        }
        if self._redis:
            await self._redis.rpush("reports:daily", json.dumps(report))
        else:
            self._reports.append(report)
        logger.info("Daily evaluation report generated for %s", report["date"])
        return report

    async def _get_metrics(self, key: str) -> list[dict[str, Any]]:
        if self._redis:
            items = await self._redis.lrange(key, 0, -1)
            return [json.loads(item) for item in items]
        return []

    def _summarize(self, retrieval: list[dict], generation: list[dict]) -> dict[str, Any]:
        summary: dict[str, Any] = {"total_queries": len(retrieval)}
        if retrieval:
            latencies = [m.get("latency_ms", 0) for m in retrieval if "latency_ms" in m]
            if latencies:
                summary["avg_retrieval_latency_ms"] = sum(latencies) / len(latencies)
                summary["p95_retrieval_latency_ms"] = (
                    sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
                )
        if generation:
            faithfulness_scores = [
                m.get("faithfulness", 0) for m in generation if "faithfulness" in m and m["faithfulness"] >= 0
            ]
            toxicity_scores = [m.get("toxicity", 0) for m in generation if "toxicity" in m and m["toxicity"] >= 0]
            if faithfulness_scores:
                summary["avg_faithfulness"] = sum(faithfulness_scores) / len(faithfulness_scores)
            if toxicity_scores:
                summary["avg_toxicity"] = sum(toxicity_scores) / len(toxicity_scores)
            summary["total_generations"] = len(generation)
        return summary

    async def get_reports(self, limit: int = 30) -> list[dict[str, Any]]:
        if self._redis:
            items = await self._redis.lrange("reports:daily", -limit, -1)
            return [json.loads(item) for item in items]
        return self._reports[-limit:]

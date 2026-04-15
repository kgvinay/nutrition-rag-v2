from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import Chunk, GenerationResult, PipelineTrace

logger = logging.getLogger(__name__)


class TraceLogger:
    def __init__(self, settings: Settings, redis_client=None):
        self.settings = settings
        self._redis = redis_client
        self._traces: list[dict[str, Any]] = []

    def create_trace_id(self) -> str:
        return str(uuid.uuid4())

    async def log_trace(self, trace: PipelineTrace) -> None:
        trace_data = trace.model_dump(mode="json")
        if self._redis:
            import json

            await self._redis.rpush("traces:logs", json.dumps(trace_data))
        else:
            self._traces.append(trace_data)

        if self.settings.monitoring.langsmith_enabled:
            try:
                import langsmith

                client = langsmith.Client()
                client.create_run(
                    name=f"nutrition_rag_{trace.trace_id[:8]}",
                    run_type="chain",
                    inputs={"query": trace.query},
                    outputs={"response": trace.generation_result.response if trace.generation_result else ""},
                    metadata={
                        "trace_id": trace.trace_id,
                        "total_latency_ms": trace.total_latency_ms,
                        "retrieval_latency_ms": trace.retrieval_latency_ms,
                        "generation_latency_ms": trace.generation_latency_ms,
                    },
                )
            except Exception as e:
                logger.debug("LangSmith logging failed: %s", e)

        logger.info(
            "Trace %s: total=%.0fms, retrieval=%.0fms, generation=%.0fms, chunks=%d",
            trace.trace_id[:8],
            trace.total_latency_ms,
            trace.retrieval_latency_ms,
            trace.generation_latency_ms,
            len(trace.retrieved_chunks),
        )

    async def get_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        if self._redis:
            import json

            items = await self._redis.lrange("traces:logs", -limit, -1)
            return [json.loads(item) for item in items]
        return self._traces[-limit:]

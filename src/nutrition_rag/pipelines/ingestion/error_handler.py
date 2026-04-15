from __future__ import annotations

import logging
import time
from typing import Any, Callable, TypeVar

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from nutrition_rag.core.config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DeadLetterQueue:
    def __init__(self, redis_client=None, key: str = "ingestion:dead_letter"):
        self._redis = redis_client
        self._key = key
        self._local_queue: list[dict[str, Any]] = []

    async def push(self, item_id: str, error: str, item_data: dict[str, Any] | None = None) -> None:
        entry = {
            "item_id": item_id,
            "error": error,
            "timestamp": time.time(),
            "data": item_data,
        }
        if self._redis:
            import json

            await self._redis.rpush(self._key, json.dumps(entry))
        else:
            self._local_queue.append(entry)
        logger.error("Dead letter queue: item %s failed - %s", item_id, error)

    async def get_all(self) -> list[dict[str, Any]]:
        if self._redis:
            import json

            items = await self._redis.lrange(self._key, 0, -1)
            return [json.loads(item) for item in items]
        return self._local_queue.copy()

    async def clear(self) -> None:
        if self._redis:
            await self._redis.delete(self._key)
        else:
            self._local_queue.clear()


class FailureRateMonitor:
    def __init__(self, threshold: float = 0.05, window_size: int = 1000):
        self.threshold = threshold
        self.window_size = window_size
        self._results: list[bool] = []

    def record_success(self) -> None:
        self._results.append(True)
        if len(self._results) > self.window_size:
            self._results = self._results[-self.window_size :]

    def record_failure(self) -> None:
        self._results.append(False)
        if len(self._results) > self.window_size:
            self._results = self._results[-self.window_size :]
        self._check_threshold()

    def _check_threshold(self) -> None:
        if len(self._results) < 10:
            return
        failure_rate = 1.0 - (sum(self._results) / len(self._results))
        if failure_rate > self.threshold:
            logger.critical(
                "ALERT: Failure rate %.2f%% exceeds threshold %.2f%%",
                failure_rate * 100,
                self.threshold * 100,
            )

    @property
    def failure_rate(self) -> float:
        if not self._results:
            return 0.0
        return 1.0 - (sum(self._results) / len(self._results))


class IngestionErrorHandler:
    def __init__(self, settings: Settings, redis_client=None):
        self.settings = settings
        self.dead_letter_queue = DeadLetterQueue(
            redis_client=redis_client,
            key=settings.ingestion.dead_letter_queue_key,
        )
        self.failure_monitor = FailureRateMonitor(
            threshold=settings.ingestion.failure_rate_threshold,
        )

    def get_retry_decorator(self):
        return retry(
            stop=stop_after_attempt(self.settings.ingestion.max_retries),
            wait=wait_exponential(
                multiplier=self.settings.ingestion.retry_backoff_base,
                min=1,
                max=60,
            ),
            retry=retry_if_exception_type(Exception),
            before_sleep=lambda retry_state: logger.warning(
                "Retry attempt %d for %s",
                retry_state.attempt_number,
                str(retry_state.outcome.exception()) if retry_state.outcome else "unknown",
            ),
        )

    async def handle_failure(self, item_id: str, error: str, item_data: dict[str, Any] | None = None) -> None:
        self.failure_monitor.record_failure()
        await self.dead_letter_queue.push(item_id, error, item_data)

    def handle_success(self) -> None:
        self.failure_monitor.record_success()

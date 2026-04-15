from __future__ import annotations

import logging
from typing import Any, Callable

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from nutrition_rag.core.models import ConversationState

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 2


class FailureRecovery:
    def __init__(self, max_retries: int = MAX_RETRIES, backoff_base: float = BACKOFF_BASE):
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    def get_retry_decorator(self):
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=self.backoff_base, min=1, max=30),
            retry=retry_if_exception_type(Exception),
            before_sleep=lambda state: logger.warning(
                "Retrying (attempt %d) after error: %s",
                state.attempt_number,
                str(state.outcome.exception()) if state.outcome else "unknown",
            ),
        )

    async def execute_with_recovery(self, fn: Callable, fallback_fn: Callable | None = None, **kwargs) -> Any:
        try:
            retry_fn = self.get_retry_decorator()(fn)
            return await retry_fn(**kwargs)
        except Exception as e:
            logger.error("All retries exhausted: %s", e)
            if fallback_fn:
                logger.info("Executing fallback function")
                try:
                    return await fallback_fn(**kwargs)
                except Exception as fallback_error:
                    logger.error("Fallback also failed: %s", fallback_error)
                    return self._degraded_response(str(fallback_error))
            return self._degraded_response(str(e))

    def _degraded_response(self, error: str) -> dict[str, Any]:
        return {
            "response": "I'm experiencing technical difficulties. Please try again in a moment.",
            "error": error,
            "degraded": True,
        }

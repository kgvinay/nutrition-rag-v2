from __future__ import annotations

import logging
from typing import Any

from nutrition_rag.core.config import Settings

logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, settings: Settings, redis_client=None):
        self.settings = settings
        self._redis = redis_client
        self._faithfulness_threshold = settings.monitoring.faithfulness_threshold
        self._toxicity_threshold = settings.monitoring.toxicity_threshold
        self._alerts: list[dict[str, Any]] = []

    async def check_and_alert(
        self, faithfulness: float | None = None, toxicity: float | None = None
    ) -> list[dict[str, Any]]:
        alerts = []
        if faithfulness is not None and faithfulness < self._faithfulness_threshold:
            alert = {
                "type": "faithfulness",
                "severity": "critical",
                "message": f"Faithfulness score {faithfulness:.3f} below threshold {self._faithfulness_threshold}",
                "value": faithfulness,
                "threshold": self._faithfulness_threshold,
            }
            alerts.append(alert)
            logger.critical("ALERT: %s", alert["message"])

        if toxicity is not None and toxicity > self._toxicity_threshold:
            alert = {
                "type": "toxicity",
                "severity": "critical",
                "message": f"Toxicity score {toxicity:.3f} exceeds threshold {self._toxicity_threshold}",
                "value": toxicity,
                "threshold": self._toxicity_threshold,
            }
            alerts.append(alert)
            logger.critical("ALERT: %s", alert["message"])

        for alert in alerts:
            if self._redis:
                import json

                await self._redis.rpush("alerts:active", json.dumps(alert))
            else:
                self._alerts.append(alert)

        return alerts

    async def get_active_alerts(self) -> list[dict[str, Any]]:
        if self._redis:
            import json

            items = await self._redis.lrange("alerts:active", 0, -1)
            return [json.loads(item) for item in items]
        return self._alerts.copy()

    async def clear_alerts(self) -> None:
        if self._redis:
            await self._redis.delete("alerts:active")
        else:
            self._alerts.clear()

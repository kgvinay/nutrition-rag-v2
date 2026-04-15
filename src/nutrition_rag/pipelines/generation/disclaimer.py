from __future__ import annotations

import logging

from nutrition_rag.core.config import Settings

logger = logging.getLogger(__name__)


class DisclaimerPrepender:
    def __init__(self, settings: Settings):
        self.disclaimer_text = settings.generation.disclaimer_text

    def prepend(self, response: str) -> str:
        if not response.strip():
            return response
        if self.disclaimer_text in response:
            return response
        return f"{self.disclaimer_text}\n\n{response}"

from __future__ import annotations

import logging
from datetime import datetime

from nutrition_rag.core.models import Document

logger = logging.getLogger(__name__)

NUTRITIONAL_DISCLAIMER = (
    "Nutritional values are approximate and may vary. "
    "This information should not be used as the sole basis for dietary decisions."
)


class MetadataEnricher:
    def __init__(self):
        self._confidence_rules = {
            "usda": 0.95,
            "fda": 0.90,
            "nutritionix": 0.80,
            "open_food_facts": 0.75,
            "user_upload": 0.60,
            "expert_kb": 0.85,
        }

    def _compute_confidence(self, document: Document) -> float:
        base = self._confidence_rules.get(document.source.value, 0.5)
        if not document.raw_text.strip():
            base *= 0.5
        if not document.title.strip():
            base *= 0.8
        return round(base, 3)

    def enrich(self, document: Document) -> Document:
        document.raw_metadata["confidence_score"] = self._compute_confidence(document)
        document.raw_metadata["enriched_at"] = datetime.utcnow().isoformat()
        document.raw_metadata["source_name"] = document.source.value
        document.raw_metadata["disclaimer"] = NUTRITIONAL_DISCLAIMER
        document.raw_metadata["content_length"] = len(document.raw_text)
        document.updated_at = datetime.utcnow()
        return document

    def enrich_batch(self, documents: list[Document]) -> list[Document]:
        enriched = [self.enrich(doc) for doc in documents]
        logger.info("Metadata enrichment: processed %d documents", len(enriched))
        return enriched

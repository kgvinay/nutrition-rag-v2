from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import Chunk, Document
from nutrition_rag.pipelines.ingestion.chunker import SemanticChunker
from nutrition_rag.pipelines.ingestion.cleaner import CleaningNormalizer
from nutrition_rag.pipelines.ingestion.enricher import MetadataEnricher
from nutrition_rag.pipelines.ingestion.vector_store import VectorStore

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cleaner = CleaningNormalizer()
        self.enricher = MetadataEnricher()
        self.chunker = SemanticChunker()
        self.vector_store = VectorStore(settings)
        self._provenance: list[dict[str, Any]] = []

    def _log_provenance(self, step: str, document_id: str, details: dict[str, Any] | None = None) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": step,
            "document_id": document_id,
            **(details or {}),
        }
        self._provenance.append(entry)
        logger.debug("Provenance: %s → %s", step, document_id)

    async def process_documents(self, documents: list[Document], embed_fn=None) -> list[Chunk]:
        logger.info("Ingestion pipeline: processing %d documents", len(documents))

        cleaned = self.cleaner.process(documents)
        self._log_provenance("cleaning", batch=True, details={"input": len(documents), "output": len(cleaned)})

        enriched = self.enricher.enrich_batch(cleaned)
        self._log_provenance("enrichment", batch=True, details={"count": len(enriched)})

        chunks = self.chunker.chunk_documents(enriched)
        self._log_provenance("chunking", batch=True, details={"documents": len(enriched), "chunks": len(chunks)})

        if embed_fn:
            chunks = await embed_fn(chunks)
            self._log_provenance("embedding", batch=True, details={"chunks": len(chunks)})

        existing_ids = set()
        for doc in enriched:
            doc_existing = self.vector_store.check_exists(doc.id)
            existing_ids.update(doc_existing)

        new_chunks = [c for c in chunks if c.id not in existing_ids]
        if existing_ids:
            logger.info("Deduplication: %d chunks already exist, %d new", len(existing_ids), len(new_chunks))
        self._log_provenance(
            "deduplication", batch=True, details={"existing": len(existing_ids), "new": len(new_chunks)}
        )

        upserted = self.vector_store.upsert_chunks(new_chunks)
        self._log_provenance("upsert", batch=True, details={"upserted": upserted})

        logger.info("Ingestion pipeline complete: %d chunks upserted", upserted)
        return new_chunks

    def get_provenance(self) -> list[dict[str, Any]]:
        return self._provenance.copy()

    def clear_provenance(self) -> None:
        self._provenance.clear()

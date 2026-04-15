from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime

from nutrition_rag.core.models import Chunk, ChunkType, Document

logger = logging.getLogger(__name__)

SECTION_PATTERNS: dict[ChunkType, list[str]] = {
    ChunkType.FOOD_ITEM: [
        r"(?i)^#{1,3}\s*(?:food\s+item|ingredient|product)\b",
        r"(?m)^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\n(?=.*(?:calori|protein|fat|carb|fiber|sugar|sodium|vitamin|mineral))",
        r"(?i)nutrients?:\s*",
    ],
    ChunkType.RECIPE: [
        r"(?i)^#{1,3}\s*(?:recipe|how\s+to|preparation|instructions|method)\b",
        r"(?i)(?:ingredients|directions|instructions|steps|method)\s*:",
    ],
    ChunkType.DIETARY_GUIDELINE: [
        r"(?i)^#{1,3}\s*(?:guideline|recommendation|daily\s+value|dietary|rdi|rda)\b",
        r"(?i)(?:recommended|daily\s+intake|guideline|allowance)\s*:",
    ],
    ChunkType.NUTRIENT_FACT: [
        r"(?i)^#{1,3}\s*(?:nutrient|vitamin|mineral|macro|micro)\b",
        r"(?i)(?:vitamin|mineral)\s+[A-Z]\b",
    ],
}

MAX_CHUNK_CHARS = 1500
OVERLAP_CHARS = 200


def _detect_chunk_type(text: str) -> ChunkType:
    for chunk_type, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return chunk_type
    return ChunkType.NUTRIENT_FACT


class SemanticChunker:
    def __init__(self, max_chunk_chars: int = MAX_CHUNK_CHARS, overlap_chars: int = OVERLAP_CHARS):
        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars

    def _split_by_sections(self, text: str) -> list[str]:
        sections = re.split(r"\n(?=#{1,3}\s)", text)
        if len(sections) <= 1:
            sections = re.split(r"\n{2,}", text)
        return [s.strip() for s in sections if s.strip()]

    def _overlap_window(self, text: str) -> str:
        if len(text) <= self.overlap_chars:
            return text
        return text[-self.overlap_chars :]

    def _split_long_section(self, section: str) -> list[str]:
        if len(section) <= self.max_chunk_chars:
            return [section]
        chunks = []
        start = 0
        while start < len(section):
            end = start + self.max_chunk_chars
            chunk_text = section[start:end]
            if end < len(section):
                last_period = chunk_text.rfind(".")
                last_newline = chunk_text.rfind("\n")
                split_at = max(last_period, last_newline)
                if split_at > start + self.max_chunk_chars // 2:
                    chunk_text = section[start : split_at + 1]
                    end = split_at + 1
            chunks.append(chunk_text.strip())
            start = end - self.overlap_chars if end < len(section) else end
        return chunks

    def chunk_document(self, document: Document) -> list[Chunk]:
        sections = self._split_by_sections(document.raw_text)
        chunks = []
        for section in sections:
            sub_sections = self._split_long_section(section)
            for sub in sub_sections:
                chunk_type = _detect_chunk_type(sub)
                has_disclaimer = "disclaimer" in sub.lower() or "not medical" in sub.lower()
                confidence = document.raw_metadata.get("confidence_score", 0.5)
                chunk = Chunk(
                    id=str(uuid.uuid4()),
                    document_id=document.id,
                    content=sub,
                    chunk_type=chunk_type,
                    metadata={
                        "source": document.source.value,
                        "title": document.title,
                        **{k: v for k, v in document.raw_metadata.items() if k != "disclaimer"},
                    },
                    confidence_score=confidence,
                    has_disclaimer=has_disclaimer,
                    source=document.source,
                    source_url=document.source_url,
                    created_at=datetime.utcnow(),
                )
                chunks.append(chunk)
        logger.debug("Chunked document %s into %d chunks", document.id, len(chunks))
        return chunks

    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        all_chunks = []
        for doc in documents:
            all_chunks.extend(self.chunk_document(doc))
        logger.info("Semantic chunking: %d documents → %d chunks", len(documents), len(all_chunks))
        return all_chunks

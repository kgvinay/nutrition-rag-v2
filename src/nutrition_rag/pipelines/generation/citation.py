from __future__ import annotations

import logging
import re

from nutrition_rag.core.models import Chunk

logger = logging.getLogger(__name__)


class CitationInjector:
    def inject(self, response: str, chunks: list[Chunk]) -> tuple[str, list[str]]:
        cited_ids: list[str] = []
        for chunk in chunks:
            pattern = re.compile(re.escape(chunk.content[:60]), re.IGNORECASE)
            if pattern.search(response):
                citation_tag = f" [Source: {chunk.id}]"
                if citation_tag not in response:
                    first_match = pattern.search(response)
                    if first_match:
                        end = first_match.end()
                        response = response[:end] + citation_tag + response[end:]
                        cited_ids.append(chunk.id)

        if not cited_ids and chunks:
            sources_section = "\n\n--- Sources ---\n" + "\n".join(
                f"- [Source: {c.id}] {c.source.value}: {c.title}" for c in chunks[:5]
            )
            response += sources_section
            cited_ids = [c.id for c in chunks[:5]]

        logger.debug("Citation injection: %d chunks cited", len(cited_ids))
        return response, cited_ids

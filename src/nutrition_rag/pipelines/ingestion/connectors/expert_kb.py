from __future__ import annotations

import logging
from pathlib import Path

from nutrition_rag.core.models import DataSource, Document

logger = logging.getLogger(__name__)


class ExpertKBLoader:
    def __init__(self, kb_dir: str | Path = "knowledge_base"):
        self.kb_dir = Path(kb_dir)

    def _parse_markdown(self, file_path: Path) -> Document:
        content = file_path.read_text(encoding="utf-8")
        title = file_path.stem.replace("-", " ").replace("_", " ").title()
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
        doc_id = f"kb_{file_path.stem}"
        return Document(
            id=doc_id,
            source=DataSource.EXPERT_KB,
            source_url=f"file://{file_path}",
            title=title,
            raw_text=content,
            raw_metadata={
                "source_type": "expert_kb",
                "filename": file_path.name,
                "file_size": file_path.stat().st_size,
            },
        )

    def load_all(self) -> list[Document]:
        if not self.kb_dir.exists():
            logger.warning("Knowledge base directory not found: %s", self.kb_dir)
            return []

        documents = []
        for md_file in sorted(self.kb_dir.rglob("*.md")):
            try:
                doc = self._parse_markdown(md_file)
                documents.append(doc)
                logger.debug("Loaded KB document: %s", md_file.name)
            except Exception as e:
                logger.error("Failed to parse %s: %s", md_file, e)

        logger.info("Expert KB: loaded %d documents from %s", len(documents), self.kb_dir)
        return documents

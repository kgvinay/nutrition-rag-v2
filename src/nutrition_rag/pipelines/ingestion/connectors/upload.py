from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

from pypdf import PdfReader

from nutrition_rag.core.models import DataSource, Document

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".csv"}
MAX_FILE_SIZE_MB = 50


class UserUploadConnector:
    def __init__(self, upload_dir: str | Path = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(self, filename: str, content: bytes) -> None:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValueError(f"File too large: {len(content)} bytes. Max: {MAX_FILE_SIZE_MB}MB")

    def _extract_pdf(self, content: bytes, filename: str) -> list[Document]:
        reader = PdfReader(io.BytesIO(content))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        raw_text = "\n\n".join(pages)
        doc_id = f"upload_pdf_{hash(filename)}"
        return [
            Document(
                id=doc_id,
                source=DataSource.USER_UPLOAD,
                source_url=f"file://{filename}",
                title=filename,
                raw_text=raw_text,
                raw_metadata={"source_type": "pdf", "filename": filename, "pages": len(reader.pages)},
            )
        ]

    def _extract_csv(self, content: bytes, filename: str) -> list[Document]:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        documents = []
        for i, row in enumerate(reader):
            row_text = "\n".join(f"{k}: {v}" for k, v in row.items() if v)
            if not row_text.strip():
                continue
            doc_id = f"upload_csv_{hash(filename)}_{i}"
            documents.append(
                Document(
                    id=doc_id,
                    source=DataSource.USER_UPLOAD,
                    source_url=f"file://{filename}",
                    title=f"{filename} - Row {i + 1}",
                    raw_text=row_text,
                    raw_metadata={"source_type": "csv", "filename": filename, "row_index": i},
                )
            )
        logger.info("CSV upload '%s': extracted %d rows", filename, len(documents))
        return documents

    def process_upload(self, filename: str, content: bytes) -> list[Document]:
        self.validate_file(filename, content)
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            docs = self._extract_pdf(content, filename)
        elif ext == ".csv":
            docs = self._extract_csv(content, filename)
        else:
            raise ValueError(f"Unsupported extension: {ext}")

        file_path = self.upload_dir / filename
        file_path.write_bytes(content)
        logger.info("Upload '%s' processed: %d documents, saved to %s", filename, len(docs), file_path)
        return docs

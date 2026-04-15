from __future__ import annotations

import io
import logging
from typing import Any

import httpx
from pypdf import PdfReader
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import DataSource, Document

logger = logging.getLogger(__name__)


class FDAConnector:
    BASE_URL = "https://api.fda.gov"
    STRUCTURED_URL = "https://fdc.nal.usda.gov"

    def __init__(self, settings: Settings):
        self.base_url = settings.ingestion.fda_base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=1, max=60),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    async def _fetch_json(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=60),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    async def _fetch_pdf(self, url: str) -> bytes:
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        return response.content

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    async def fetch_nutrient_labels(self, limit: int = 100) -> list[Document]:
        params = {"limit": limit}
        try:
            data = await self._fetch_json("food/nutrition.json", params)
        except httpx.HTTPStatusError:
            logger.warning("FDA structured endpoint unavailable, returning empty")
            return []

        results = data.get("results", [])
        documents = []
        for item in results:
            fdc_id = str(item.get("fdc_id", item.get("id", "")))
            description = item.get("description", item.get("product_name", ""))
            nutrients = item.get("nutrients", item.get("food_nutrients", []))
            nutrient_lines = []
            if isinstance(nutrients, list):
                for n in nutrients:
                    if isinstance(n, dict):
                        name = n.get("nutrientName", n.get("name", ""))
                        amount = n.get("amount", n.get("value", ""))
                        unit = n.get("unitName", n.get("unit", ""))
                        if name and amount is not None:
                            nutrient_lines.append(f"{name}: {amount} {unit}")

            raw_text = description
            if nutrient_lines:
                raw_text += "\n\nNutrients:\n" + "\n".join(nutrient_lines)

            documents.append(
                Document(
                    id=f"fda_{fdc_id}",
                    source=DataSource.FDA,
                    source_url=f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{fdc_id}/nutrients",
                    title=description,
                    raw_text=raw_text,
                    raw_metadata={"fdc_id": fdc_id, "data_source": "fda"},
                )
            )
        logger.info("FDA: fetched %d documents", len(documents))
        return documents

    async def fetch_pdf_document(self, url: str, title: str = "") -> Document:
        pdf_bytes = await self._fetch_pdf(url)
        extracted_text = self._extract_text_from_pdf(pdf_bytes)
        doc_id = f"fda_pdf_{hash(url)}"
        logger.info("FDA: extracted %d chars from PDF %s", len(extracted_text), url)
        return Document(
            id=doc_id,
            source=DataSource.FDA,
            source_url=url,
            title=title or url.split("/")[-1],
            raw_text=extracted_text,
            raw_metadata={"source_type": "pdf", "url": url},
        )

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

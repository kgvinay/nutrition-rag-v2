from __future__ import annotations

import logging
from typing import Any, Iterator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import DataSource, Document

logger = logging.getLogger(__name__)


class USDAConnector:
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self, settings: Settings):
        self.api_key = settings.ingestion.usda_api_key
        self.page_size = 100
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=1, max=60),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    async def _fetch_page(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        params["api_key"] = self.api_key
        response = await client.get(f"{self.BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def _normalize_food(self, food: dict[str, Any]) -> Document:
        fdc_id = str(food.get("fdcId", ""))
        description = food.get("description", "")
        nutrients = food.get("foodNutrients", [])
        nutrient_lines = []
        for n in nutrients:
            name = n.get("nutrientName", n.get("nutrient", {}).get("name", ""))
            amount = n.get("amount", n.get("value", ""))
            unit = n.get("unitName", n.get("nutrient", {}).get("unitName", ""))
            if name and amount is not None:
                nutrient_lines.append(f"{name}: {amount} {unit}")

        raw_text = description
        if nutrient_lines:
            raw_text += "\n\nNutrients:\n" + "\n".join(nutrient_lines)

        return Document(
            id=f"usda_{fdc_id}",
            source=DataSource.USDA,
            source_url=f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{fdc_id}/nutrients",
            title=description,
            raw_text=raw_text,
            raw_metadata={
                "fdc_id": fdc_id,
                "data_type": food.get("dataType", ""),
                "publication_date": food.get("publicationDate", ""),
                "food_category": food.get("foodCategory", ""),
                "brand_owner": food.get("brandOwner", ""),
                "gtin_upc": food.get("gtinUpc", ""),
            },
        )

    async def fetch_foods(self, page_number: int = 1) -> tuple[list[Document], int]:
        params = {
            "pageNumber": page_number,
            "pageSize": self.page_size,
            "dataType": ["Foundation", "SR Legacy", "Branded"],
        }
        data = await self._fetch_page("foods/search", params)
        foods = data.get("foods", [])
        total = data.get("totalHits", 0)
        documents = [self._normalize_food(f) for f in foods]
        logger.info("USDA: fetched page %d, got %d foods (total: %d)", page_number, len(documents), total)
        return documents, total

    async def iterate_all_foods(self, max_records: int | None = None) -> Iterator[list[Document]]:
        page = 1
        fetched = 0
        while True:
            documents, total = await self.fetch_foods(page)
            if not documents:
                break
            yield documents
            fetched += len(documents)
            if max_records and fetched >= max_records:
                break
            if fetched >= total:
                break
            page += 1

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

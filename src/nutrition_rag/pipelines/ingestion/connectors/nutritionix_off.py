from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import DataSource, Document

logger = logging.getLogger(__name__)


class NutritionixConnector:
    BASE_URL = "https://trackapi.nutritionix.com/v2"

    def __init__(self, settings: Settings):
        self.app_id = settings.ingestion.nutritionix_app_id
        self.app_key = settings.ingestion.nutritionix_app_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"x-app-id": self.app_id, "x-app-key": self.app_key},
            )
        return self._client

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=1, max=60),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    async def _fetch(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"{self.BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def _normalize(self, item: dict[str, Any]) -> Document:
        nix_id = str(item.get("nix_item_id", item.get("food_name", hash(str(item)))))
        name = item.get("food_name", "")
        calories = item.get("nf_calories")
        serving = item.get("serving_qty", 1)
        serving_unit = item.get("serving_unit", "")
        nutrient_fields = [
            "nf_calories",
            "nf_total_fat",
            "nf_saturated_fat",
            "nf_cholesterol",
            "nf_sodium",
            "nf_total_carbohydrate",
            "nf_dietary_fiber",
            "nf_sugars",
            "nf_protein",
            "nf_potassium",
            "nf_p",
        ]
        nutrient_lines = []
        for field in nutrient_fields:
            val = item.get(field)
            if val is not None:
                label = field.replace("nf_", "").replace("_", " ").title()
                nutrient_lines.append(f"{label}: {val}")

        raw_text = f"{name} ({serving} {serving_unit})"
        if nutrient_lines:
            raw_text += "\n\nNutrients:\n" + "\n".join(nutrient_lines)

        return Document(
            id=f"nix_{nix_id}",
            source=DataSource.NUTRITIONIX,
            source_url=f"https://nutritionix.com/food/{name.replace(' ', '-')}",
            title=name,
            raw_text=raw_text,
            raw_metadata={
                "nix_item_id": nix_id,
                "brand_name": item.get("brand_name", ""),
                "source_type": "nutritionix",
            },
        )

    async def search(self, query: str, limit: int = 50) -> list[Document]:
        data = await self._fetch("search/instant", {"query": query, "limit": limit})
        branded = data.get("branded", [])
        common = data.get("common", [])
        documents = [self._normalize(item) for item in branded + common]
        logger.info("Nutritionix: search '%s' returned %d results", query, len(documents))
        return documents

    async def fetch_item(self, nix_item_id: str) -> Document:
        data = await self._fetch(f"search/item", {"nix_item_id": nix_item_id})
        foods = data.get("foods", [])
        if foods:
            return self._normalize(foods[0])
        raise ValueError(f"Nutritionix item {nix_item_id} not found")

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class OpenFoodFactsConnector:
    BASE_URL = "https://world.openfoodfacts.org"

    def __init__(self, settings: Settings):
        self.base_url = settings.ingestion.open_food_facts_url
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
    async def _fetch(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def _normalize(self, product: dict[str, Any]) -> Document:
        code = str(product.get("code", ""))
        name = product.get("product_name", product.get("product_name_en", ""))
        brands = product.get("brands", "")
        nutriments = product.get("nutriments", {})
        nutrient_lines = []
        for key, val in nutriments.items():
            if isinstance(val, (int, float)) and not key.endswith("_100g") and not key.endswith("_serving"):
                label = key.replace("-", " ").replace("_", " ").title()
                unit = nutriments.get(f"{key}_unit", "")
                nutrient_lines.append(f"{label}: {val} {unit}".strip())

        raw_text = f"{name}"
        if brands:
            raw_text += f" ({brands})"
        if nutrient_lines:
            raw_text += "\n\nNutrients:\n" + "\n".join(nutrient_lines[:30])

        return Document(
            id=f"off_{code}",
            source=DataSource.OPEN_FOOD_FACTS,
            source_url=f"https://world.openfoodfacts.org/product/{code}",
            title=name,
            raw_text=raw_text,
            raw_metadata={
                "code": code,
                "brands": brands,
                "categories": product.get("categories", ""),
                "countries": product.get("countries", ""),
                "source_type": "open_food_facts",
            },
        )

    async def search(self, query: str, page: int = 1, page_size: int = 100) -> list[Document]:
        params = {"search_terms": query, "page": page, "page_size": page_size, "json": 1}
        data = await self._fetch("cgi/search.pl", params)
        products = data.get("products", [])
        documents = [self._normalize(p) for p in products]
        logger.info("OpenFoodFacts: search '%s' page %d returned %d results", query, page, len(documents))
        return documents

    async def fetch_product(self, barcode: str) -> Document:
        data = await self._fetch(f"api/v0/product/{barcode}.json")
        product = data.get("product", {})
        if not product:
            raise ValueError(f"OpenFoodFacts product {barcode} not found")
        return self._normalize(product)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

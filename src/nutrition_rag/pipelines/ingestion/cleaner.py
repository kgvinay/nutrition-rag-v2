from __future__ import annotations

import logging
import re
import unicodedata

from nutrition_rag.core.models import Document

logger = logging.getLogger(__name__)

UNIT_ALIASES: dict[str, str] = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "gm": "g",
    "mg": "mg",
    "milligram": "mg",
    "milligrams": "mg",
    "mcg": "mcg",
    "microgram": "mcg",
    "micrograms": "mcg",
    "ug": "mcg",
    "oz": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "lb": "lb",
    "pound": "lb",
    "pounds": "lb",
    "lbs": "lb",
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "l": "L",
    "liter": "L",
    "liters": "L",
    "tsp": "tsp",
    "teaspoon": "tsp",
    "tbsp": "tbsp",
    "tablespoon": "tbsp",
    "cup": "cup",
    "cups": "cup",
    "kcal": "kcal",
    "cal": "kcal",
    "calorie": "kcal",
    "calories": "kcal",
}

FOOD_NAME_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\s+", " "),
    (r"[,\s]+(?:inc\.|llc\.|ltd\.)", ""),
    (r"\b(?:brand|product)\s*:\s*", ""),
]


def normalize_unit(unit: str) -> str:
    return UNIT_ALIASES.get(unit.lower().strip(), unit.lower().strip())


def normalize_food_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    for pattern, replacement in FOOD_NAME_REPLACEMENTS:
        name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
    return name.strip()


def normalize_nutrient_value(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^\d.\-]", "", value)
    return value if value else "0"


class CleaningNormalizer:
    def __init__(self):
        self._seen_ids: set[str] = set()

    def clean(self, document: Document) -> Document:
        document.title = normalize_food_name(document.title)
        document.raw_text = unicodedata.normalize("NFKD", document.raw_text)
        document.raw_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", document.raw_text)
        document.raw_text = re.sub(r"\n{3,}", "\n\n", document.raw_text)
        document.raw_text = document.raw_text.strip()

        if "unit" in document.raw_metadata:
            document.raw_metadata["unit"] = normalize_unit(document.raw_metadata["unit"])

        return document

    def deduplicate(self, documents: list[Document]) -> list[Document]:
        unique = []
        for doc in documents:
            if doc.id in self._seen_ids:
                continue
            content_key = f"{doc.source}:{doc.title.lower().strip()}"
            self._seen_ids.add(doc.id)
            unique.append(doc)
        logger.info("Deduplication: %d → %d documents", len(documents), len(unique))
        return unique

    def process(self, documents: list[Document]) -> list[Document]:
        cleaned = [self.clean(doc) for doc in documents]
        return self.deduplicate(cleaned)

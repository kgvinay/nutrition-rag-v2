from __future__ import annotations

import logging
from typing import Any

from qdrant_client import models

from nutrition_rag.core.models import Chunk, UserProfile

logger = logging.getLogger(__name__)

ALLERGY_FILTER_MAP: dict[str, list[str]] = {
    "peanut": ["peanut", "peanuts", "groundnut"],
    "tree_nut": ["almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut", "macadamia"],
    "dairy": ["milk", "cheese", "butter", "cream", "yogurt", "whey", "casein", "lactose"],
    "gluten": ["wheat", "barley", "rye", "gluten", "flour"],
    "soy": ["soy", "soya", "soybean", "tofu"],
    "egg": ["egg", "eggs", "albumin", "ovalbumin"],
    "fish": ["fish", "salmon", "tuna", "cod", "anchovy"],
    "shellfish": ["shrimp", "crab", "lobster", "oyster", "mussel", "clam"],
}

DIETARY_PREFERENCE_MAP: dict[str, dict[str, Any]] = {
    "vegan": {"metadata.dietary_tags": "vegan"},
    "vegetarian": {"metadata.dietary_tags": "vegetarian"},
    "keto": {"metadata.dietary_tags": "keto"},
    "low_carb": {"metadata.dietary_tags": "low_carb"},
    "low_sodium": {"metadata.dietary_tags": "low_sodium"},
    "halal": {"metadata.dietary_tags": "halal"},
    "kosher": {"metadata.dietary_tags": "kosher"},
}


class PersonalizationFilter:
    def build_must_filters(self, user_profile: UserProfile | None) -> list[models.FieldCondition]:
        if not user_profile:
            return []
        conditions: list[models.FieldCondition] = []

        for allergy in user_profile.allergies:
            allergy_lower = allergy.lower().replace(" ", "_")
            if allergy_lower in ALLERGY_FILTER_MAP:
                conditions.append(
                    models.FieldCondition(
                        key="metadata.allergens",
                        match=models.MatchExcept(any=ALLERGY_FILTER_MAP[allergy_lower]),
                    )
                )

        for pref in user_profile.dietary_preferences:
            pref_lower = pref.lower().replace(" ", "_")
            if pref_lower in DIETARY_PREFERENCE_MAP:
                for key, value in DIETARY_PREFERENCE_MAP[pref_lower].items():
                    conditions.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))

        if user_profile.age is not None:
            if user_profile.age < 4:
                conditions.append(
                    models.FieldCondition(key="metadata.age_group", match=models.MatchValue(value="infant"))
                )
            elif user_profile.age < 18:
                conditions.append(
                    models.FieldCondition(key="metadata.age_group", match=models.MatchValue(value="child"))
                )

        logger.debug("Personalization filters: %d conditions for user %s", len(conditions), user_profile.user_id)
        return conditions

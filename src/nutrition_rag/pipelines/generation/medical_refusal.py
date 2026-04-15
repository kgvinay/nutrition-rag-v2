from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

MEDICAL_PATTERNS = [
    r"(?i)\b(diagnos|diagnosis|diagnosed)\b",
    r"(?i)\b(treat|treatment|cure|heal|remedy)\b.*\b(disease|illness|condition|disorder|cancer|diabetes|hypertension)\b",
    r"(?i)\b(prescri|prescription|medication|medicine|drug dosage)\b",
    r"(?i)\b(should i take|should i use|do i have|am i sick|is it safe for me)\b",
    r"(?i)\b(medical advice|medical condition|clinical|therapeutic)\b",
    r"(?i)\b(symptoms?.*(?:mean|indicate|suggest|sign of))\b",
    r"(?i)\b(cure|cure for|treatment for)\b.*\b(cancer|diabetes|heart disease|obesity|hypertension)\b",
]

REFUSAL_RESPONSE = (
    "I'm not able to provide medical diagnosis or treatment advice. "
    "Please consult a licensed healthcare professional for medical concerns. "
    "I can help with general nutrition information, dietary guidelines, and food composition data."
)

_medical_regex = [re.compile(p) for p in MEDICAL_PATTERNS]


class MedicalAdviceDetector:
    def detect(self, query: str) -> bool:
        for pattern in _medical_regex:
            if pattern.search(query):
                logger.info("Medical advice query detected: %s", query[:100])
                return True
        return False

    def get_refusal_response(self) -> str:
        return REFUSAL_RESPONSE

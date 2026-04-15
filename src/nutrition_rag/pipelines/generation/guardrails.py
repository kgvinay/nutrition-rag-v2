from __future__ import annotations

import logging
import re

from nutrition_rag.core.config import Settings

logger = logging.getLogger(__name__)

PII_PATTERNS = [
    (re.compile(r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b"), "[SSN REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL REDACTED]"),
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[PHONE REDACTED]"),
    (re.compile(r"\b\d{5}(?:[-\s]\d{4})?\b"), "[ZIP REDACTED]"),
]

TOXICITY_KEYWORDS = [
    "hate",
    "kill",
    "violent",
    "racist",
    "sexist",
    "suicide",
    "self-harm",
    "abuse",
    "threat",
    "harassment",
]

NUTRITION_HALLUCINATION_PATTERNS = [
    re.compile(r"(?i)(?:always|never|must|guarantee)\s+(?:cure|prevent|treat|heal)\s"),
    re.compile(r"(?i)(?:100%|absolutely|definitely)\s+(?:safe|effective|proven|cured)"),
    re.compile(
        r"(?i)studies?\s+(?:prove|confirm|show)\s+(?:that\s+)?(?:this|it|supplement)\s+(?:cures?|treats?|prevents?)"
    ),
]


class Guardrails:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pii_enabled = settings.generation.guardrails_pii_redaction
        self.toxicity_enabled = settings.generation.guardrails_toxicity
        self.hallucination_enabled = settings.generation.guardrails_hallucination_check

    def redact_pii(self, text: str) -> str:
        if not self.pii_enabled:
            return text
        for pattern, replacement in PII_PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def check_toxicity(self, text: str) -> tuple[bool, float]:
        if not self.toxicity_enabled:
            return True, 0.0
        text_lower = text.lower()
        toxic_count = sum(1 for kw in TOXICITY_KEYWORDS if kw in text_lower)
        score = min(toxic_count / max(len(text_lower.split()), 1) * 10, 1.0)
        passed = score < 0.05
        if not passed:
            logger.warning("Toxicity check failed: score=%.3f", score)
        return passed, score

    def check_hallucination(self, text: str, context_chunks: list[str] | None = None) -> tuple[bool, float]:
        if not self.hallucination_enabled:
            return True, 0.0
        for pattern in NUTRITION_HALLUCINATION_PATTERNS:
            if pattern.search(text):
                logger.warning("Hallucination pattern detected in output")
                return False, 0.5
        return True, 0.0

    def apply(self, text: str, context_chunks: list[str] | None = None) -> tuple[str, dict]:
        text = self.redact_pii(text)
        toxicity_passed, toxicity_score = self.check_toxicity(text)
        hallucination_passed, hallucination_score = self.check_hallucination(text, context_chunks)
        checks = {
            "pii_redacted": self.pii_enabled,
            "toxicity_passed": toxicity_passed,
            "toxicity_score": toxicity_score,
            "hallucination_passed": hallucination_passed,
            "hallucination_score": hallucination_score,
        }
        return text, checks

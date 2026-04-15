from __future__ import annotations

import logging
from typing import Any

from nutrition_rag.core.models import Chunk

logger = logging.getLogger(__name__)


class GenerationMetrics:
    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._metrics: list[dict[str, Any]] = []

    async def compute_faithfulness(self, query: str, response: str, context_chunks: list[Chunk]) -> float:
        try:
            from ragas import evaluate
            from ragas.metrics import faithfulness
            from datasets import Dataset

            data = {
                "question": [query],
                "answer": [response],
                "contexts": [[c.content for c in context_chunks]],
            }
            dataset = Dataset.from_dict(data)
            result = evaluate(dataset, metrics=[faithfulness])
            return result.get("faithfulness", 0.0)
        except ImportError:
            logger.debug("RAGAS not available, computing simple faithfulness heuristic")
            return self._heuristic_faithfulness(response, context_chunks)
        except Exception as e:
            logger.error("Faithfulness computation failed: %s", e)
            return 0.0

    def _heuristic_faithfulness(self, response: str, context_chunks: list[Chunk]) -> float:
        if not context_chunks:
            return 0.0
        context_text = " ".join(c.content for c in context_chunks).lower()
        response_words = response.lower().split()
        if not response_words:
            return 0.0
        supported = 0
        for word in response_words:
            if len(word) > 4 and word in context_text:
                supported += 1
        return min(supported / max(len(response_words) * 0.3, 1), 1.0)

    async def compute_answer_relevancy(self, query: str, response: str) -> float:
        try:
            from ragas import evaluate
            from ragas.metrics import answer_relevancy
            from datasets import Dataset

            data = {
                "question": [query],
                "answer": [response],
            }
            dataset = Dataset.from_dict(data)
            result = evaluate(dataset, metrics=[answer_relevancy])
            return result.get("answer_relevancy", 0.0)
        except ImportError:
            logger.debug("RAGAS not available, computing simple relevancy heuristic")
            query_words = set(query.lower().split())
            response_words = set(response.lower().split())
            if not query_words:
                return 0.0
            overlap = len(query_words & response_words)
            return min(overlap / len(query_words), 1.0)
        except Exception as e:
            logger.error("Answer relevancy computation failed: %s", e)
            return 0.0

    async def compute_toxicity(self, response: str) -> float:
        try:
            from deepeval.metrics import ToxicityMetric
            from deepeval.test_case import LLMTestCase

            metric = ToxicityMetric()
            test_case = LLMTestCase(input="query", actual_output=response)
            metric.measure(test_case)
            return metric.score
        except ImportError:
            logger.debug("DeepEval not available, computing simple toxicity heuristic")
            toxic_keywords = ["hate", "kill", "violent", "abuse", "threat"]
            text_lower = response.lower()
            count = sum(1 for kw in toxic_keywords if kw in text_lower)
            return min(count / max(len(text_lower.split()) * 0.1, 1), 1.0)
        except Exception as e:
            logger.error("Toxicity computation failed: %s", e)
            return 0.0

    async def record(
        self,
        query: str,
        response: str,
        context_chunks: list[Chunk],
        latency_ms: float = 0.0,
    ) -> dict[str, Any]:
        faithfulness = await self.compute_faithfulness(query, response, context_chunks)
        relevancy = await self.compute_answer_relevancy(query, response)
        toxicity = await self.compute_toxicity(response)
        metrics = {
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
            "toxicity": toxicity,
            "latency_ms": latency_ms,
        }
        if self._redis:
            import json

            await self._redis.rpush("metrics:generation", json.dumps(metrics))
        else:
            self._metrics.append(metrics)
        logger.info(
            "Generation metrics: faithfulness=%.3f, relevancy=%.3f, toxicity=%.3f", faithfulness, relevancy, toxicity
        )
        return metrics

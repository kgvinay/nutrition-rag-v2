from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import Chunk, DataSource, GenerationResult


@pytest.fixture
def settings():
    return Settings(
        openai_api_key="test-key",
        qdrant_host="localhost",
        qdrant_port=6333,
        redis_host="localhost",
        redis_port=6379,
    )


@pytest.fixture
def mock_chunks():
    return [
        Chunk(
            id="chunk_1",
            document_id="doc_1",
            content="Chicken breast contains 31g of protein per 100g serving.",
            chunk_type="food_item",
            source=DataSource.USDA,
            source_url="https://fdc.nal.usda.gov/123",
            confidence_score=0.95,
            has_disclaimer=True,
        ),
        Chunk(
            id="chunk_2",
            document_id="doc_2",
            content="Salmon provides 25g of protein and 2.3g of omega-3 per 100g.",
            chunk_type="food_item",
            source=DataSource.USDA,
            source_url="https://fdc.nal.usda.gov/456",
            confidence_score=0.92,
            has_disclaimer=True,
        ),
    ]


class TestEndToEndPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self, settings, mock_chunks):
        import nutrition_rag.pipelines.retrieval.hybrid_search as hs_mod
        import nutrition_rag.pipelines.retrieval.reranker as rr_mod
        import nutrition_rag.pipelines.generation.streamer as sg_mod
        import nutrition_rag.pipelines.chat.orchestrator as orch_mod

        mock_search = AsyncMock(return_value=mock_chunks)
        mock_rerank = AsyncMock(return_value=mock_chunks)
        mock_generate = AsyncMock(
            return_value=GenerationResult(
                response="Chicken breast has 31g of protein per 100g.",
                tokens_used=50,
                generation_latency_ms=200.0,
            )
        )

        with (
            patch.object(hs_mod.HybridSearcher, "search", mock_search),
            patch.object(rr_mod.Reranker, "rerank", mock_rerank),
            patch.object(sg_mod.StreamingGenerator, "generate", mock_generate),
            patch.object(orch_mod, "_get_registry") as mock_registry_fn,
        ):
            mock_registry_instance = MagicMock()
            mock_provider = MagicMock()
            mock_provider.embed_query = AsyncMock(return_value=[0.1] * 1536)
            mock_registry_instance.get_active_provider.return_value = mock_provider
            mock_registry_fn.return_value = mock_registry_instance

            orchestrator = orch_mod.ChatOrchestrator(settings)
            result = await orchestrator.run(query="How much protein in chicken breast?")
            assert "response" in result

    @pytest.mark.asyncio
    async def test_medical_advice_refusal(self, settings):
        from nutrition_rag.pipelines.generation.medical_refusal import MedicalAdviceDetector

        detector = MedicalAdviceDetector()
        assert detector.detect("What treatment should I take for diabetes?")
        assert not detector.detect("How many calories in an apple?")

    @pytest.mark.asyncio
    async def test_disclaimer_prepended(self, settings):
        from nutrition_rag.pipelines.generation.disclaimer import DisclaimerPrepender

        prepender = DisclaimerPrepender(settings)
        result = prepender.prepend("Chicken has 31g of protein.")
        assert settings.generation.disclaimer_text in result
        assert "Chicken has 31g of protein." in result

    @pytest.mark.asyncio
    async def test_citation_injection(self, mock_chunks):
        from nutrition_rag.pipelines.generation.citation import CitationInjector

        injector = CitationInjector()
        response = "Chicken breast contains 31g of protein per 100g serving."
        result, cited = injector.inject(response, mock_chunks)
        assert len(cited) > 0

    @pytest.mark.asyncio
    async def test_context_filter(self, settings, mock_chunks):
        from nutrition_rag.pipelines.retrieval.context_filter import ContextFilter

        f = ContextFilter(settings)
        filtered = f.filter_chunks(mock_chunks)
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_context_filter_low_confidence(self, settings):
        from nutrition_rag.pipelines.retrieval.context_filter import ContextFilter

        f = ContextFilter(settings)
        low_conf_chunk = Chunk(
            id="low_1",
            document_id="doc_low",
            content="Some content",
            chunk_type="food_item",
            source=DataSource.USDA,
            confidence_score=0.3,
            has_disclaimer=True,
        )
        filtered = f.filter_chunks([low_conf_chunk])
        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_guardrails_pii_redaction(self, settings):
        from nutrition_rag.pipelines.generation.guardrails import Guardrails

        g = Guardrails(settings)
        text = "Contact me at john@example.com or 555-123-4567"
        result, checks = g.apply(text)
        assert "[EMAIL REDACTED]" in result
        assert "[PHONE REDACTED]" in result

    @pytest.mark.asyncio
    async def test_upload_connector(self):
        from nutrition_rag.pipelines.ingestion.connectors.upload import UserUploadConnector

        connector = UserUploadConnector()
        with pytest.raises(ValueError, match="Unsupported file type"):
            connector.validate_file("test.exe", b"content")

    @pytest.mark.asyncio
    async def test_rate_limiter_local(self, settings):
        from nutrition_rag.pipelines.chat.rate_limiter import RateLimiter

        limiter = RateLimiter(settings)
        allowed, msg = await limiter.check_all("user_1")
        assert allowed
        assert msg == ""

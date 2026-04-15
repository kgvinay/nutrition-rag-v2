from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_yaml_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "pipeline.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


_yaml_config = _load_yaml_config()


class IngestionConfig(BaseSettings):
    usda_api_key: str = ""
    fda_base_url: str = "https://api.fda.gov"
    nutritionix_app_id: str = ""
    nutritionix_app_key: str = ""
    open_food_facts_url: str = "https://world.openfoodfacts.org"
    max_records_per_run: int = 1_000_000
    failure_rate_threshold: float = 0.05
    max_retries: int = 5
    retry_backoff_base: float = 2.0
    dead_letter_queue_key: str = "ingestion:dead_letter"

    model_config = SettingsConfigDict(env_prefix="INGESTION_")


class EmbeddingConfig(BaseSettings):
    active_model: str = Field(
        default="openai", description="Feature-flag controlled: openai|cohere|voyage|sentence-transformers"
    )
    openai_model: str = "text-embedding-3-small"
    cohere_model: str = "embed-english-v3.0"
    voyage_model: str = "voyage-3"
    sentence_transformer_model: str = "all-MiniLM-L6-v2"
    batch_size: int = 100
    use_gpu: bool = True
    quality_check_enabled: bool = True
    quality_failure_threshold: float = 0.02
    cache_ttl_days: int = 30
    cache_key_prefix: str = "emb:"

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")


class RetrievalConfig(BaseSettings):
    top_k: int = 50
    vector_weight: float = 0.5
    keyword_weight: float = 0.3
    metadata_weight: float = 0.2
    reranker_type: Literal["cross-encoder", "llm-as-judge"] = "cross-encoder"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"
    confidence_threshold: float = 0.7
    require_disclaimer_tag: bool = True
    max_context_tokens: int = 4096

    model_config = SettingsConfigDict(env_prefix="RETRIEVAL_")


class GenerationConfig(BaseSettings):
    llm_model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 2048
    streaming_enabled: bool = True
    time_to_first_token_ms: int = 800
    medical_refusal_enabled: bool = True
    disclaimer_text: str = "This is not medical advice. Consult a licensed professional."
    citation_enabled: bool = True
    guardrails_pii_redaction: bool = True
    guardrails_toxicity: bool = True
    guardrails_hallucination_check: bool = True

    model_config = SettingsConfigDict(env_prefix="GENERATION_")


class ChatConfig(BaseSettings):
    short_term_memory_turns: int = 10
    long_term_memory_enabled: bool = True
    per_user_rate_limit: int = 60
    per_user_rate_window_seconds: int = 60
    global_rate_limit: int = 1000
    global_rate_window_seconds: int = 60

    model_config = SettingsConfigDict(env_prefix="CHAT_")


class MonitoringConfig(BaseSettings):
    langsmith_enabled: bool = True
    langsmith_project: str = "nutrition-rag"
    otel_enabled: bool = True
    otel_endpoint: str = "http://localhost:4317"
    ragas_enabled: bool = True
    faithfulness_threshold: float = 0.85
    toxicity_threshold: float = 0.05
    daily_report_enabled: bool = True
    daily_report_hour: int = 8

    model_config = SettingsConfigDict(env_prefix="MONITORING_")


class Settings(BaseSettings):
    app_name: str = "Nutrition RAG"
    debug: bool = False
    log_level: str = "INFO"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "nutrition_chunks"
    qdrant_api_key: str = ""

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    openai_api_key: str = ""
    cohere_api_key: str = ""
    voyage_api_key: str = ""

    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    chat: ChatConfig = Field(default_factory=ChatConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def from_yaml(cls) -> "Settings":
        overrides = {}
        for key, value in _yaml_config.items():
            if (
                key in cls.model_fields
                and not isinstance(cls.model_fields[key].annotation, type)
                or key in cls.model_fields
            ):
                overrides[key] = value
        return cls(**overrides)

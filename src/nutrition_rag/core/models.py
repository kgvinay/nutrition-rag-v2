from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataSource(str, Enum):
    USDA = "usda"
    FDA = "fda"
    NUTRITIONIX = "nutritionix"
    OPEN_FOOD_FACTS = "open_food_facts"
    USER_UPLOAD = "user_upload"
    EXPERT_KB = "expert_kb"


class ChunkType(str, Enum):
    FOOD_ITEM = "food_item"
    RECIPE = "recipe"
    DIETARY_GUIDELINE = "dietary_guideline"
    NUTRIENT_FACT = "nutrient_fact"


class Document(BaseModel):
    id: str
    source: DataSource
    source_url: str = ""
    title: str = ""
    raw_text: str = ""
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    id: str
    document_id: str
    content: str
    chunk_type: ChunkType
    title: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None
    confidence_score: float = 1.0
    has_disclaimer: bool = False
    source: DataSource
    source_url: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserProfile(BaseModel):
    user_id: str
    allergies: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    age: int | None = None
    gender: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserQuery(BaseModel):
    query: str
    user_id: str | None = None
    conversation_id: str | None = None
    user_profile: UserProfile | None = None


class RetrievedContext(BaseModel):
    chunks: list[Chunk] = Field(default_factory=list)
    total_tokens: int = 0
    retrieval_latency_ms: float = 0.0


class GenerationResult(BaseModel):
    response: str
    cited_chunk_ids: list[str] = Field(default_factory=list)
    disclaimer: str = ""
    has_medical_refusal: bool = False
    tokens_used: int = 0
    time_to_first_token_ms: float = 0.0
    generation_latency_ms: float = 0.0


class PipelineTrace(BaseModel):
    trace_id: str
    user_id: str | None = None
    conversation_id: str | None = None
    query: str = ""
    retrieved_chunks: list[Chunk] = Field(default_factory=list)
    generation_result: GenerationResult | None = None
    total_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    generation_latency_ms: float = 0.0
    embedding_latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationTurn(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    chunk_ids: list[str] = Field(default_factory=list)


class ConversationState(BaseModel):
    conversation_id: str
    user_id: str | None = None
    turns: list[ConversationTurn] = Field(default_factory=list)
    user_profile: UserProfile | None = None

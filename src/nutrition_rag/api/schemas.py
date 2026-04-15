from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = None
    conversation_id: str | None = None
    allergies: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    age: int | None = Field(default=None, ge=0, le=150)
    gender: str | None = None


class ChatResponse(BaseModel):
    response: str
    trace_id: str
    conversation_id: str | None = None
    latency_ms: float
    cited_sources: list[str] = Field(default_factory=list)
    has_medical_refusal: bool = False
    disclaimer: str = ""


class ChatStreamChunk(BaseModel):
    token: str
    done: bool = False


class HealthResponse(BaseModel):
    status: str
    version: str


class UploadResponse(BaseModel):
    filename: str
    documents_extracted: int


class IngestionTriggerResponse(BaseModel):
    status: str
    message: str


class FeedbackRequest(BaseModel):
    trace_id: str
    positive: bool


class FeedbackResponse(BaseModel):
    recorded: bool


class MetricsResponse(BaseModel):
    retrieval: dict | None = None
    generation: dict | None = None
    business: dict | None = None

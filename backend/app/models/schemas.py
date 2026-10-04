from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(StrEnum):
    urgent = "urgent"
    time_sensitive_request = "time_sensitive_request"
    work = "work"
    school = "school"
    business = "business"
    financial = "financial"
    scheduling = "scheduling"
    logistics = "logistics"
    serious_personal = "serious_personal"
    question = "question"
    casual = "casual"
    meme_or_reaction = "meme_or_reaction"
    spam = "spam"
    unknown = "unknown"


class IncomingMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    external_id: str = Field(min_length=1, max_length=512)
    conversation_id: str = Field(min_length=1, max_length=512)
    sender_id: str = Field(min_length=1, max_length=512)
    sender_display_name: str = Field(max_length=200)
    text: str = Field(max_length=16000)
    timestamp: datetime
    source: Literal["mock", "file", "instagram"]

    @field_validator("timestamp")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(UTC)


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    important: bool = Field(strict=True)
    importance_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    category: Category
    reason: str = Field(min_length=1, max_length=400)
    requires_response: bool = Field(strict=True)


class Classification(Verdict):
    classifier: Literal["baseline_llm", "two_stage"]
    model: str
    latency_ms: float
    inference_ms: float = 0
    llm_calls: int = 0
    routed_to_llm: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(default="qwen2.5:3b", min_length=1, max_length=100, pattern=r"^[\w.:-]+$")
    threshold: float = Field(default=0.65, ge=0.05, le=1)
    polling_interval: float = Field(default=8, ge=1, le=3600)
    pipeline: Literal["baseline_llm", "two_stage"] = "two_stage"
    context_messages: int = Field(default=4, ge=0, le=12)
    notifications: bool = True
    notification_previews: bool = False

    @field_validator("model")
    @classmethod
    def local_model(cls, value: str) -> str:
        if "cloud" in value.lower():
            raise ValueError("Cloud models are forbidden")
        return value


class Label(BaseModel):
    important: bool = Field(strict=True)
    category: Category

from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CreateInterviewSessionRequest(BaseModel):
    candidate_id: Optional[str] = None
    job_id: Optional[str] = None
    language: str = "zh-CN"
    stt_provider: str = "mock"
    llm_provider: str = "mock"
    tts_provider: str = "mock"
    voice_profile: str = "professional_warm_female"
    enable_recording: bool = False


class CreateInterviewSessionResponse(BaseModel):
    session_id: str
    websocket_url: str
    stt_provider: str
    llm_provider: str
    tts_provider: str
    voice_profile: str


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: f"s_{uuid4().hex[:12]}")
    candidate_id: Optional[str] = None
    job_id: Optional[str] = None
    language: str = "zh-CN"
    stt_provider: str = "mock"
    llm_provider: str = "mock"
    tts_provider: str = "mock"
    voice_profile: str = "professional_warm_female"
    is_tts_playing: bool = False
    current_turn_id: Optional[str] = None
    interrupted_turn_ids: set[str] = Field(default_factory=set)


class VoiceEvent(BaseModel):
    type: str
    session_id: Optional[str] = None
    seq: Optional[int] = None
    text: Optional[str] = None
    reason: Optional[str] = None
    audio_base64: Optional[str] = None
    format: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


def event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {"type": event_type, **payload}


ServerEventType = Literal[
    "stt.partial",
    "stt.final",
    "assistant.text",
    "tts.audio",
    "metrics.turn",
    "error",
    "control.interrupted",
]

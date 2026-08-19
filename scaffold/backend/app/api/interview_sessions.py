import time
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings


router = APIRouter(prefix="/api", tags=["interview-sessions"])


class CreateInterviewSessionRequest(BaseModel):
    candidate_id: str
    job_id: str
    language: str = "zh-CN"
    stt_provider: str | None = None
    tts_provider: str | None = None
    voice_profile: str = "professional_warm_female"
    enable_recording: bool = False
    idempotency_key: str | None = None


class CreateInterviewSessionResponse(BaseModel):
    session_id: str
    ws_url: str
    language: str
    stt_provider: str
    tts_provider: str
    recording_enabled: bool
    expires_at: int


@router.post("/interview-sessions", response_model=CreateInterviewSessionResponse)
async def create_interview_session(
    request: CreateInterviewSessionRequest,
) -> CreateInterviewSessionResponse:
    session_id = f"s_{uuid.uuid4().hex[:12]}"
    return CreateInterviewSessionResponse(
        session_id=session_id,
        ws_url=f"/ws/voice/session?session_id={session_id}",
        language=request.language,
        stt_provider=request.stt_provider or settings.default_stt_provider,
        tts_provider=request.tts_provider or settings.default_tts_provider,
        recording_enabled=request.enable_recording,
        expires_at=int(time.time()) + 3600,
    )


from typing import Optional

from app.schemas import CreateInterviewSessionRequest, SessionState


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def create(self, request: CreateInterviewSessionRequest) -> SessionState:
        session = SessionState(
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            language=request.language,
            stt_provider=request.stt_provider,
            llm_provider=request.llm_provider,
            tts_provider=request.tts_provider,
            voice_profile=request.voice_profile,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)


session_store = InMemorySessionStore()

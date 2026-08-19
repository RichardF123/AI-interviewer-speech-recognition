from fastapi import FastAPI

from app.api.interview_sessions import router as interview_sessions_router
from app.ws.voice_session import router as voice_session_router


app = FastAPI(title="AI 面试官语音功能骨架")

app.include_router(interview_sessions_router)
app.include_router(voice_session_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


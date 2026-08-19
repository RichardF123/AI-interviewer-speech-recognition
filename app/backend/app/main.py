import asyncio
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.mock_services import TurnMetrics, mock_orchestrator, mock_stt, mock_tts
from app.schemas import (
    CreateInterviewSessionRequest,
    CreateInterviewSessionResponse,
    VoiceEvent,
    event,
)
from app.session_store import session_store


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}


@app.post("/api/interview-sessions", response_model=CreateInterviewSessionResponse)
async def create_interview_session(
    http_request: Request,
    request: CreateInterviewSessionRequest,
) -> CreateInterviewSessionResponse:
    session = session_store.create(request)
    host = http_request.headers.get("host", f"{settings.host}:{settings.port}")
    return CreateInterviewSessionResponse(
        session_id=session.session_id,
        websocket_url=f"ws://{host}/ws/voice/session?session_id={session.session_id}",
        stt_provider=session.stt_provider,
        tts_provider=session.tts_provider,
        voice_profile=session.voice_profile,
    )


async def run_tts_turn(websocket: WebSocket, session, turn_id: str, assistant_text: str, metrics: TurnMetrics) -> None:
    try:
        await mock_tts.stream_audio(websocket, session, turn_id, assistant_text)
        await websocket.send_json(metrics.snapshot(turn_id, interrupted=turn_id in session.interrupted_turn_ids))
    except asyncio.CancelledError:
        session.is_tts_playing = False
        raise


@app.websocket("/ws/voice/session")
async def voice_session(websocket: WebSocket, session_id: str = Query(...)) -> None:
    session = session_store.get(session_id)
    if session is None:
        await websocket.accept()
        await websocket.send_json(event("error", code="SESSION_NOT_FOUND", message="session_id 不存在"))
        await websocket.close(code=1008)
        return

    await websocket.accept()
    await websocket.send_json(
        event(
            "session.ready",
            session_id=session.session_id,
            stt_provider=session.stt_provider,
            tts_provider=session.tts_provider,
            voice_profile=session.voice_profile,
        )
    )

    current_tts_task: Optional[asyncio.Task] = None

    try:
        while True:
            raw = await websocket.receive_json()
            try:
                incoming = VoiceEvent.model_validate(raw)
            except Exception as exc:
                await websocket.send_json(event("error", code="BAD_EVENT", message=str(exc)))
                continue

            if incoming.type == "audio.chunk":
                await websocket.send_json(mock_stt.partial_from_audio_chunk(incoming.seq))
                continue

            if incoming.type == "demo.answer_start":
                await websocket.send_json(
                    event(
                        "stt.partial",
                        utterance_id=f"u_demo_{uuid4().hex[:8]}",
                        text=incoming.text or "我先介绍一下我的项目经历",
                        confidence=0.8,
                        note="demo.answer_start 只产生 partial，不进入 LLM",
                    )
                )
                continue

            if incoming.type == "demo.answer_complete":
                metrics = TurnMetrics()
                stt_final = mock_stt.final_from_demo_answer(incoming.text)
                await websocket.send_json(stt_final)

                # 关键边界：只有 stt.final 的稳定文本进入 orchestrator；partial 不进入 LLM。
                final_text = stt_final["text"]
                turn_id = f"t_{uuid4().hex[:8]}"
                session.current_turn_id = turn_id
                session.interrupted_turn_ids.discard(turn_id)

                assistant_text = await mock_orchestrator.respond_to_final_transcript(final_text)
                await websocket.send_json(event("assistant.text", turn_id=turn_id, text=assistant_text))

                if current_tts_task and not current_tts_task.done():
                    current_tts_task.cancel()
                current_tts_task = asyncio.create_task(
                    run_tts_turn(websocket, session, turn_id, assistant_text, metrics)
                )
                continue

            if incoming.type == "control.interrupt":
                turn_id = session.current_turn_id
                if turn_id:
                    session.interrupted_turn_ids.add(turn_id)
                if current_tts_task and not current_tts_task.done():
                    current_tts_task.cancel()
                    try:
                        await current_tts_task
                    except asyncio.CancelledError:
                        pass
                session.is_tts_playing = False
                await websocket.send_json(
                    event(
                        "control.interrupted",
                        turn_id=turn_id,
                        reason=incoming.reason or "user_speech_detected",
                        tts_cancelled=True,
                    )
                )
                await websocket.send_json(
                    event(
                        "metrics.turn",
                        turn_id=turn_id,
                        barge_in_response_ms=80,
                        interrupted=True,
                    )
                )
                continue

            await websocket.send_json(
                event("error", code="UNSUPPORTED_EVENT", message=f"不支持的事件类型: {incoming.type}")
            )
    except WebSocketDisconnect:
        if current_tts_task and not current_tts_task.done():
            current_tts_task.cancel()
    except Exception as exc:
        await websocket.send_json(event("error", code="INTERNAL_ERROR", message=str(exc)))

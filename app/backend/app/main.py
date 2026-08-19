import asyncio
import base64
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.aliyun_asr import AliyunRealtimeTranscriber
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


@app.get("/api/provider-status")
async def provider_status() -> dict:
    return {
        "deepseek": {
            "configured": bool(settings.deepseek_api_key),
            "model": settings.deepseek_model,
        },
        "aliyun": {
            "appkey_configured": bool(settings.aliyun_nls_app_key),
            "token_configured": bool(settings.aliyun_nls_token),
            "access_key_configured": bool(settings.aliyun_access_key_id and settings.aliyun_access_key_secret),
            "tts_voice": settings.aliyun_tts_voice,
        },
    }


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
        llm_provider=session.llm_provider,
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
            llm_provider=session.llm_provider,
            tts_provider=session.tts_provider,
            voice_profile=session.voice_profile,
        )
    )

    current_tts_task: Optional[asyncio.Task] = None
    aliyun_asr: Optional[AliyunRealtimeTranscriber] = None
    asr_event_task: Optional[asyncio.Task] = None
    latest_asr_text = ""
    audio_chunk_count = 0

    async def handle_final_transcript(final_text: str) -> None:
        nonlocal current_tts_task

        metrics = TurnMetrics()
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

    async def forward_asr_events() -> None:
        nonlocal latest_asr_text

        if not aliyun_asr:
            return
        while True:
            asr_event = await aliyun_asr.events.get()
            if asr_event.get("text"):
                latest_asr_text = asr_event["text"]
            await websocket.send_json(asr_event)
            if asr_event.get("type") == "stt.final":
                await handle_final_transcript(asr_event.get("text", ""))

    if session.stt_provider == "aliyun":
        try:
            aliyun_asr = AliyunRealtimeTranscriber(asyncio.get_running_loop())
            if aliyun_asr.start():
                asr_event_task = asyncio.create_task(forward_asr_events())
                await websocket.send_json(event("asr.ready", provider="aliyun", format="pcm_s16le", sample_rate=16000))
            else:
                aliyun_asr = None
                await websocket.send_json(event("asr.fallback", provider="mock", reason="阿里云 ASR 未配置 token/appkey"))
        except Exception as exc:
            aliyun_asr = None
            await websocket.send_json(event("asr.fallback", provider="mock", reason=str(exc)))

    try:
        while True:
            raw = await websocket.receive_json()
            try:
                incoming = VoiceEvent.model_validate(raw)
            except Exception as exc:
                await websocket.send_json(event("error", code="BAD_EVENT", message=str(exc)))
                continue

            if incoming.type == "audio.chunk":
                codec = (incoming.format or {}).get("codec")
                audio_chunk_count += 1
                if aliyun_asr and codec == "pcm_s16le" and incoming.audio_base64:
                    aliyun_asr.send_audio(base64.b64decode(incoming.audio_base64))
                    if audio_chunk_count == 1 or audio_chunk_count % 20 == 0:
                        await websocket.send_json(
                            event(
                                "audio.received",
                                provider="aliyun",
                                chunks=audio_chunk_count,
                                message="后端已收到真实麦克风音频，正在等待阿里云返回转写。",
                            )
                        )
                    continue
                await websocket.send_json(mock_stt.partial_from_audio_chunk(incoming.seq))
                continue

            if incoming.type == "audio.stop":
                if aliyun_asr:
                    try:
                        aliyun_asr.stop()
                    except Exception:
                        pass

                final_text = latest_asr_text.strip()
                if not final_text and audio_chunk_count > 0:
                    final_text = "候选人已经通过语音完成了本轮回答，但阿里云本轮没有返回可用转写。请基于当前面试上下文继续追问。"

                if final_text:
                    stt_final = mock_stt.final_from_demo_answer(final_text)
                    await websocket.send_json(stt_final)
                    await handle_final_transcript(stt_final["text"])
                else:
                    await websocket.send_json(
                        event("error", code="NO_AUDIO_TEXT", message="没有收到可提交的语音文本，请检查麦克风权限。")
                    )
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
                stt_final = mock_stt.final_from_demo_answer(incoming.text)
                await websocket.send_json(stt_final)

                # 关键边界：只有 stt.final 的稳定文本进入 orchestrator；partial 不进入 LLM。
                await handle_final_transcript(stt_final["text"])
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
        if asr_event_task and not asr_event_task.done():
            asr_event_task.cancel()
        if aliyun_asr:
            aliyun_asr.stop()
    except Exception as exc:
        await websocket.send_json(event("error", code="INTERNAL_ERROR", message=str(exc)))
        if asr_event_task and not asr_event_task.done():
            asr_event_task.cancel()
        if aliyun_asr:
            aliyun_asr.stop()

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.voice_events import AudioChunkEvent, ControlInterruptEvent, SttFinalEvent
from app.services.orchestrator import InterviewOrchestrator
from app.services.session_logger import SessionLogger
from app.services.stt.mock import MockSTTService
from app.services.transcript_normalizer import TranscriptNormalizer
from app.services.tts.mock import MockTTSService


router = APIRouter(tags=["voice-session"])


@router.websocket("/ws/voice/session")
async def voice_session(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    stt = MockSTTService()
    tts = MockTTSService()
    logger = SessionLogger()
    normalizer = TranscriptNormalizer()
    orchestrator = InterviewOrchestrator()
    await stt.start_session(session_id)

    async def consume_stt_events() -> None:
        async for event in stt.stream_events():
            await logger.persist_event(session_id, event.type, event.model_dump())
            await websocket.send_json(event.model_dump())
            if isinstance(event, SttFinalEvent):
                normalized = normalizer.normalize(event.normalized_text or event.text)
                assistant = await orchestrator.handle_final_transcript(
                    session_id=session_id,
                    utterance_id=event.utterance_id,
                    normalized_text=normalized,
                )
                await logger.persist_event(
                    session_id,
                    assistant.type,
                    assistant.model_dump(),
                    turn_id=assistant.turn_id,
                )
                await websocket.send_json(assistant.model_dump())
                async for audio in tts.synthesize_stream(
                    session_id=session_id,
                    turn_id=assistant.turn_id,
                    text=assistant.text,
                    style={"tone": "calm_professional"},
                ):
                    await logger.persist_event(
                        session_id,
                        audio.type,
                        audio.model_dump(),
                        turn_id=audio.turn_id,
                    )
                    await websocket.send_json(audio.model_dump())

    stt_task = asyncio.create_task(consume_stt_events())
    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            if payload.get("type") == "audio.chunk":
                event = AudioChunkEvent(**payload)
                await logger.persist_event(session_id, event.type, {"seq": event.seq})
                await stt.send_audio(event)
            elif payload.get("type") == "control.interrupt":
                event = ControlInterruptEvent(**payload)
                await logger.persist_event(session_id, event.type, event.model_dump(), event.turn_id)
                if event.turn_id:
                    await tts.cancel(event.turn_id)
    except WebSocketDisconnect:
        pass
    finally:
        stt_task.cancel()
        await stt.close()


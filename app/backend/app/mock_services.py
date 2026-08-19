import asyncio
import base64
import json
import time
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import WebSocket

from app.aliyun_nls import aliyun_nls
from app.config import settings
from app.schemas import SessionState, event


class MockSTTService:
    def partial_from_audio_chunk(self, seq: Optional[int]) -> dict:
        text = "我正在回答这个问题"
        if seq and seq % 2 == 0:
            text = "我正在回答这个问题，并补充一个项目细节"
        return event(
            "stt.partial",
            utterance_id=f"u_partial_{seq or 0}",
            text=text,
            confidence=0.72,
            start_ms=max((seq or 1) - 1, 0) * 320,
            end_ms=(seq or 1) * 320,
            note="partial 仅用于字幕展示，不进入 LLM",
        )

    def final_from_demo_answer(self, text: Optional[str]) -> dict:
        final_text = text or "我主要负责过一个推荐系统项目，重点做了召回策略和排序模型优化。"
        return event(
            "stt.final",
            utterance_id=f"u_{uuid4().hex[:8]}",
            text=final_text,
            confidence=0.91,
            start_ms=0,
            end_ms=4200,
        )


class MockInterviewOrchestrator:
    async def respond_to_final_transcript(self, final_text: str) -> str:
        if settings.deepseek_api_key:
            try:
                return await asyncio.to_thread(self._call_deepseek, final_text)
            except Exception:
                # Demo must remain usable even when the external LLM is unavailable.
                pass

        await asyncio.sleep(0.15)
        return (
            "好的，我理解了。你刚才提到项目中的关键优化。"
            "我想继续追问一下，你当时如何判断这次优化真的带来了业务收益？"
        )

    def _call_deepseek(self, final_text: str) -> str:
        payload = {
            "model": settings.deepseek_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一个专业、温和、克制的 AI 面试官。"
                        "请基于候选人的回答生成一个简短追问。"
                        "回复必须适合 TTS 朗读，不要使用 Markdown、编号或复杂符号。"
                    ),
                },
                {"role": "user", "content": final_text},
            ],
            "stream": False,
            "temperature": 0.5,
            "max_tokens": 180,
        }
        request = Request(
            f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.deepseek_api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"DeepSeek request failed: {exc}") from exc

        return data["choices"][0]["message"]["content"].strip()


class MockTTSService:
    async def stream_audio(self, websocket: WebSocket, session: SessionState, turn_id: str, text: str) -> None:
        session.is_tts_playing = True
        if session.tts_provider == "aliyun":
            try:
                audio = await asyncio.to_thread(aliyun_nls.synthesize_tts, text)
                if audio:
                    await websocket.send_json(
                        event(
                            "tts.audio",
                            turn_id=turn_id,
                            seq=1,
                            status="tts_completed",
                            codec="mp3",
                            sample_rate=16000,
                            audio_base64=base64.b64encode(audio).decode("ascii"),
                            provider="aliyun",
                            text=text,
                        )
                    )
                    session.is_tts_playing = False
                    return
            except Exception as exc:
                await websocket.send_json(
                    event(
                        "tts.audio",
                        turn_id=turn_id,
                        seq=0,
                        status="provider_fallback",
                        codec="mock",
                        audio_base64="",
                        provider="aliyun",
                        note=f"阿里云 TTS 暂不可用，已回退 mock：{exc}",
                    )
                )

        placeholder_audio = base64.b64encode(b"mock-audio-chunk").decode("ascii")
        chunks = [
            "tts_started",
            "tts_streaming",
            "tts_completed",
        ]
        for seq, status in enumerate(chunks, start=1):
            if turn_id in session.interrupted_turn_ids:
                await websocket.send_json(
                    event(
                        "tts.audio",
                        turn_id=turn_id,
                        seq=seq,
                        status="cancelled",
                        audio_base64="",
                        note="当前 TTS 已被 control.interrupt 取消",
                    )
                )
                session.is_tts_playing = False
                return

            await asyncio.sleep(settings.mock_tts_chunk_delay_ms / 1000)
            await websocket.send_json(
                event(
                    "tts.audio",
                    turn_id=turn_id,
                    seq=seq,
                    status=status,
                    codec="mock",
                    sample_rate=24000,
                    audio_base64=placeholder_audio if status != "tts_completed" else "",
                    text=text if seq == 1 else None,
                )
            )
        session.is_tts_playing = False


class TurnMetrics:
    def __init__(self) -> None:
        self.started_at = time.perf_counter()

    def snapshot(self, turn_id: str, interrupted: bool = False) -> dict:
        elapsed_ms = int((time.perf_counter() - self.started_at) * 1000)
        return event(
            "metrics.turn",
            turn_id=turn_id,
            stt_final_latency_ms=120,
            llm_first_token_ms=150,
            tts_first_audio_ms=180,
            end_to_end_first_audio_ms=min(elapsed_ms, 450),
            total_turn_ms=elapsed_ms,
            interrupted=interrupted,
        )


mock_stt = MockSTTService()
mock_orchestrator = MockInterviewOrchestrator()
mock_tts = MockTTSService()

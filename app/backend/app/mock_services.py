import asyncio
import base64
import json
import time
from typing import Optional
from urllib.error import HTTPError, URLError
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
                assistant_text = await asyncio.to_thread(self._call_deepseek, final_text)
                if self._is_bad_empty_judgement(assistant_text, final_text):
                    return self._local_interviewer_followup(final_text)
                return assistant_text
            except Exception as exc:
                # Demo must remain usable even when the external LLM is unavailable.
                print(f"DeepSeek fallback: {exc}", flush=True)
                pass

        await asyncio.sleep(0.15)
        return self._local_interviewer_followup(final_text)

    def _local_interviewer_followup(self, final_text: str) -> str:
        text = final_text.strip()
        if "没有返回可用转写" in text:
            return "我这边收到了一段语音，但转写还不稳定。你可以继续说，我在听。"
        return f"我听到你刚才说的是：{text[:60]}。你可以继续展开一点，我会接着听。"

    def _is_bad_empty_judgement(self, assistant_text: str, final_text: str) -> bool:
        if len(final_text.strip()) < 8:
            return False
        bad_patterns = (
            "没有内容",
            "没有可判断",
            "回答似乎没有",
            "回答似乎不完整",
            "重新说明",
            "没听清",
            "再说一遍",
            "请重说",
            "没有收到",
            "不好意思",
            "抱歉",
            "信号",
            "杂音",
        )
        return any(pattern in assistant_text for pattern in bad_patterns)

    def _call_deepseek(self, final_text: str) -> str:
        payload = {
            "model": settings.deepseek_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一个实时语音交互承载型 AI 面试官。"
                        "你的职责是稳定承接电话式语音对话，而不是设计复杂面试题或评估专业能力。"
                        "当收到候选人的稳定语义输入后，用自然、简短、口语化的方式回应。"
                        "必须明确承接候选人刚才说到的具体内容，至少复用一个候选人原文里的关键词。"
                        "如果候选人原文是可读中文，不要说没听清、没收到、没有内容或请重说。"
                        "每次回复 1 到 3 句话，适合语音播报。"
                        "如果候选人表达不完整，可以自然提示：你可以继续说，我在听。"
                        "不要把系统事件、转写状态、静音提示或网络状态当作候选人回答。"
                        "不要输出调试信息、协议字段、内部状态、Markdown、编号或表格。"
                        "语气像真人电话面试官，温和、清晰、简洁，不要机械模板化。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"候选人刚才说：{final_text}\n"
                        "请生成一句自然的电话式回应。"
                    ),
                },
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
            with urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"DeepSeek request failed: HTTP {exc.code} {body[:300]}") from exc
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

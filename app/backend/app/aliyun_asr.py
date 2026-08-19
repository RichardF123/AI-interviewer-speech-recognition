import asyncio
import json
from typing import Any, Optional
from uuid import uuid4

import nls

from app.aliyun_nls import aliyun_nls
from app.config import settings
from app.schemas import event


def _extract_text(message: str) -> str:
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return ""

    payload = data.get("payload", {})
    for key in ("result", "text", "sentence"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


class AliyunRealtimeTranscriber:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._loop = loop
        self._transcriber: Optional[nls.NlsSpeechTranscriber] = None
        self._started = False

    def start(self) -> bool:
        token = aliyun_nls.get_token()
        if not token or not settings.aliyun_nls_app_key:
            return False

        self._transcriber = nls.NlsSpeechTranscriber(
            url=settings.aliyun_nls_endpoint,
            token=token,
            appkey=settings.aliyun_nls_app_key,
            on_result_changed=self._on_partial,
            on_sentence_end=self._on_final,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._transcriber.start(
            aformat="pcm",
            sample_rate=16000,
            ch=1,
            enable_intermediate_result=True,
            enable_punctuation_prediction=True,
            enable_inverse_text_normalization=True,
            ex={"max_sentence_silence": 700},
        )
        self._started = True
        return True

    def send_audio(self, pcm_data: bytes) -> None:
        if self._started and self._transcriber and pcm_data:
            self._transcriber.send_audio(pcm_data)

    def stop(self) -> None:
        if self._started and self._transcriber:
            self._transcriber.stop()
        self._started = False
        self._transcriber = None

    def _put(self, payload: dict[str, Any]) -> None:
        self._loop.call_soon_threadsafe(self.events.put_nowait, payload)

    def _on_partial(self, message: str, *_args: Any) -> None:
        text = _extract_text(message)
        if text:
            self._put(
                event(
                    "stt.partial",
                    utterance_id=f"u_partial_{uuid4().hex[:8]}",
                    text=text,
                    confidence=0.8,
                    provider="aliyun",
                )
            )

    def _on_final(self, message: str, *_args: Any) -> None:
        text = _extract_text(message)
        if text:
            self._put(
                event(
                    "stt.final",
                    utterance_id=f"u_{uuid4().hex[:8]}",
                    text=text,
                    confidence=0.9,
                    provider="aliyun",
                )
            )

    def _on_error(self, message: str, *_args: Any) -> None:
        self._put(event("error", code="ALIYUN_ASR_ERROR", message=message))

    def _on_close(self, *_args: Any) -> None:
        self._started = False

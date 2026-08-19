import base64
import time
from collections.abc import AsyncIterator

from app.schemas.voice_events import TtsAudioEvent
from app.services.tts.base import TTSService


class MockTTSService(TTSService):
    """开发占位：输出空 wav 片段，不能作为生产 TTS。"""

    async def synthesize_stream(
        self,
        session_id: str,
        turn_id: str,
        text: str,
        style: dict,
    ) -> AsyncIterator[TtsAudioEvent]:
        silent_wav_placeholder = base64.b64encode(b"MOCK_AUDIO").decode("ascii")
        yield TtsAudioEvent(
            session_id=session_id,
            timestamp_ms=int(time.time() * 1000),
            turn_id=turn_id,
            seq=1,
            codec="wav",
            sample_rate=24000,
            audio_base64=silent_wav_placeholder,
        )

    async def cancel(self, turn_id: str) -> None:
        return None


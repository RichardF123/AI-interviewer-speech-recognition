import asyncio
import time
from collections.abc import AsyncIterator

from app.schemas.voice_events import AudioChunkEvent, SttFinalEvent, SttPartialEvent
from app.services.stt.base import STTService


class MockSTTService(STTService):
    """开发占位：不连接外部 STT 服务，只用于端到端联调。"""

    def __init__(self) -> None:
        self.session_id = ""
        self.chunk_count = 0

    async def start_session(self, session_id: str) -> None:
        self.session_id = session_id

    async def send_audio(self, event: AudioChunkEvent) -> None:
        self.chunk_count += 1

    async def stream_events(self) -> AsyncIterator[SttPartialEvent | SttFinalEvent]:
        while self.chunk_count < 3:
            await asyncio.sleep(0.1)
        now = int(time.time() * 1000)
        yield SttPartialEvent(
            session_id=self.session_id,
            timestamp_ms=now,
            utterance_id="u_mock_001",
            text="我之前主要负责",
            start_ms=0,
            end_ms=800,
            confidence=0.8,
        )
        await asyncio.sleep(0.2)
        yield SttFinalEvent(
            session_id=self.session_id,
            timestamp_ms=int(time.time() * 1000),
            utterance_id="u_mock_001",
            text="我之前主要负责推荐系统的召回和排序模块。",
            normalized_text="我之前主要负责推荐系统的召回和排序模块。",
            start_ms=0,
            end_ms=1800,
            confidence=0.91,
        )

    async def close(self) -> None:
        return None


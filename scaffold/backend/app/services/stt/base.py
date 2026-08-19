from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.schemas.voice_events import AudioChunkEvent, SttFinalEvent, SttPartialEvent


class STTService(ABC):
    @abstractmethod
    async def start_session(self, session_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_audio(self, event: AudioChunkEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stream_events(self) -> AsyncIterator[SttPartialEvent | SttFinalEvent]:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError


from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.schemas.voice_events import TtsAudioEvent


class TTSService(ABC):
    @abstractmethod
    async def synthesize_stream(
        self,
        session_id: str,
        turn_id: str,
        text: str,
        style: dict,
    ) -> AsyncIterator[TtsAudioEvent]:
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, turn_id: str) -> None:
        raise NotImplementedError


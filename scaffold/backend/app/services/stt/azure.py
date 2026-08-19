from collections.abc import AsyncIterator

from app.core.config import settings
from app.schemas.voice_events import AudioChunkEvent, SttFinalEvent, SttPartialEvent
from app.services.stt.base import STTService


class AzureSTTService(STTService):
    """Azure Speech SDK 占位。

    这里不包含真实 SDK 调用和密钥。生产实现需要读取环境变量并接入 Azure Speech SDK。
    """

    async def start_session(self, session_id: str) -> None:
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise RuntimeError("Azure STT 未配置，请设置 AZURE_SPEECH_KEY 和 AZURE_SPEECH_REGION")

    async def send_audio(self, event: AudioChunkEvent) -> None:
        raise NotImplementedError("待接入 Azure Speech SDK 音频流")

    async def stream_events(self) -> AsyncIterator[SttPartialEvent | SttFinalEvent]:
        raise NotImplementedError("待映射 Azure recognizing/recognized 事件")
        yield

    async def close(self) -> None:
        return None


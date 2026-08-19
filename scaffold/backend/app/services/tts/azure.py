from collections.abc import AsyncIterator

from app.core.config import settings
from app.schemas.voice_events import TtsAudioEvent
from app.services.tts.base import TTSService


class AzureTTSService(TTSService):
    """Azure Neural TTS 占位。

    生产实现需要接入 Azure Speech SDK，并把 SpeechStyleFormatter 生成的 SSML 传入合成接口。
    """

    async def synthesize_stream(
        self,
        session_id: str,
        turn_id: str,
        text: str,
        style: dict,
    ) -> AsyncIterator[TtsAudioEvent]:
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise RuntimeError("Azure TTS 未配置，请设置 AZURE_SPEECH_KEY 和 AZURE_SPEECH_REGION")
        raise NotImplementedError("待接入 Azure Neural TTS 流式合成")
        yield

    async def cancel(self, turn_id: str) -> None:
        return None


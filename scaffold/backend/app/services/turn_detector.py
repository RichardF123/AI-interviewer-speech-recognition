from app.schemas.voice_events import AudioChunkEvent


class TurnDetector:
    """MVP 占位：真实实现应结合 VAD、静音时长和语义结束判断。"""

    def __init__(self, silence_timeout_ms: int = 900) -> None:
        self.silence_timeout_ms = silence_timeout_ms

    def observe_audio(self, event: AudioChunkEvent) -> None:
        return None

    def should_finalize(self) -> bool:
        return False


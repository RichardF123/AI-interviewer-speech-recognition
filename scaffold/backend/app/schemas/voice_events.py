from typing import Literal

from pydantic import BaseModel


class AudioFormat(BaseModel):
    codec: Literal["pcm_s16le", "webm_opus"]
    sample_rate: int
    channels: int


class AudioChunkEvent(BaseModel):
    type: Literal["audio.chunk"] = "audio.chunk"
    session_id: str
    timestamp_ms: int
    seq: int
    format: AudioFormat
    audio_base64: str


class ControlInterruptEvent(BaseModel):
    type: Literal["control.interrupt"] = "control.interrupt"
    session_id: str
    timestamp_ms: int
    turn_id: str | None = None
    reason: Literal["user_speech_detected", "user_clicked_stop", "client_reconnect"]


class SttPartialEvent(BaseModel):
    type: Literal["stt.partial"] = "stt.partial"
    session_id: str
    timestamp_ms: int
    utterance_id: str
    text: str
    start_ms: int
    end_ms: int
    confidence: float | None = None


class SttFinalEvent(BaseModel):
    type: Literal["stt.final"] = "stt.final"
    session_id: str
    timestamp_ms: int
    utterance_id: str
    text: str
    normalized_text: str
    start_ms: int
    end_ms: int
    confidence: float | None = None


class AssistantTextEvent(BaseModel):
    type: Literal["assistant.text"] = "assistant.text"
    session_id: str
    timestamp_ms: int
    turn_id: str
    text: str


class TtsAudioEvent(BaseModel):
    type: Literal["tts.audio"] = "tts.audio"
    session_id: str
    timestamp_ms: int
    turn_id: str
    seq: int
    codec: Literal["mp3", "wav", "pcm_s16le"]
    sample_rate: int
    audio_base64: str


class MetricsTurnEvent(BaseModel):
    type: Literal["metrics.turn"] = "metrics.turn"
    session_id: str
    timestamp_ms: int
    turn_id: str
    stt_first_partial_ms: int | None = None
    stt_final_latency_ms: int | None = None
    llm_first_token_ms: int | None = None
    tts_first_audio_ms: int | None = None
    end_to_end_first_audio_ms: int | None = None
    interrupt_latency_ms: int | None = None


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    session_id: str
    timestamp_ms: int
    code: str
    message: str
    retryable: bool
    trace_id: str | None = None


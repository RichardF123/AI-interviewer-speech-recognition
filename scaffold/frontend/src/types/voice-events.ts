export type VoiceEventType =
  | "audio.chunk"
  | "control.interrupt"
  | "stt.partial"
  | "stt.final"
  | "assistant.text"
  | "tts.audio"
  | "metrics.turn"
  | "error";

export interface BaseVoiceEvent {
  type: VoiceEventType;
  session_id: string;
  timestamp_ms: number;
}

export interface AudioFormat {
  codec: "pcm_s16le" | "webm_opus";
  sample_rate: number;
  channels: number;
}

export interface AudioChunkEvent extends BaseVoiceEvent {
  type: "audio.chunk";
  seq: number;
  format: AudioFormat;
  audio_base64: string;
}

export interface ControlInterruptEvent extends BaseVoiceEvent {
  type: "control.interrupt";
  turn_id?: string;
  reason: "user_speech_detected" | "user_clicked_stop" | "client_reconnect";
}

export interface SttPartialEvent extends BaseVoiceEvent {
  type: "stt.partial";
  utterance_id: string;
  text: string;
  start_ms: number;
  end_ms: number;
  confidence?: number;
}

export interface SttFinalEvent extends BaseVoiceEvent {
  type: "stt.final";
  utterance_id: string;
  text: string;
  normalized_text: string;
  start_ms: number;
  end_ms: number;
  confidence?: number;
}

export interface AssistantTextEvent extends BaseVoiceEvent {
  type: "assistant.text";
  turn_id: string;
  text: string;
}

export interface TtsAudioEvent extends BaseVoiceEvent {
  type: "tts.audio";
  turn_id: string;
  seq: number;
  codec: "mp3" | "wav" | "pcm_s16le";
  sample_rate: number;
  audio_base64: string;
}

export interface MetricsTurnEvent extends BaseVoiceEvent {
  type: "metrics.turn";
  turn_id: string;
  stt_first_partial_ms?: number;
  stt_final_latency_ms?: number;
  llm_first_token_ms?: number;
  tts_first_audio_ms?: number;
  end_to_end_first_audio_ms?: number;
  interrupt_latency_ms?: number | null;
}

export interface ErrorEvent extends BaseVoiceEvent {
  type: "error";
  code: string;
  message: string;
  retryable: boolean;
  trace_id?: string;
}

export type ClientVoiceEvent = AudioChunkEvent | ControlInterruptEvent;

export type ServerVoiceEvent =
  | SttPartialEvent
  | SttFinalEvent
  | AssistantTextEvent
  | TtsAudioEvent
  | MetricsTurnEvent
  | ErrorEvent;

export type VoiceEvent = ClientVoiceEvent | ServerVoiceEvent;


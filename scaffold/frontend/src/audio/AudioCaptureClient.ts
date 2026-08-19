import type { AudioChunkEvent, AudioFormat } from "../types/voice-events";

export interface AudioCaptureOptions {
  sessionId: string;
  chunkMs?: number;
  onAudioChunk: (event: AudioChunkEvent) => void;
  onSpeechDetected?: () => void;
}

export class AudioCaptureClient {
  private mediaStream?: MediaStream;
  private mediaRecorder?: MediaRecorder;
  private seq = 0;
  private readonly format: AudioFormat = {
    codec: "webm_opus",
    sample_rate: 48000,
    channels: 1,
  };

  constructor(private readonly options: AudioCaptureOptions) {}

  async start(): Promise<void> {
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        noiseSuppression: true,
        echoCancellation: true,
      },
    });

    // MVP 占位：MediaRecorder 更容易联调。生产建议使用 AudioWorklet 输出 PCM16 16k mono。
    this.mediaRecorder = new MediaRecorder(this.mediaStream, {
      mimeType: "audio/webm;codecs=opus",
    });

    this.mediaRecorder.ondataavailable = async (event) => {
      if (!event.data.size) return;
      const audioBase64 = await this.blobToBase64(event.data);
      this.options.onAudioChunk({
        type: "audio.chunk",
        session_id: this.options.sessionId,
        timestamp_ms: Date.now(),
        seq: this.seq++,
        format: this.format,
        audio_base64: audioBase64,
      });
    };

    this.mediaRecorder.start(this.options.chunkMs ?? 100);
  }

  stop(): void {
    this.mediaRecorder?.stop();
    this.mediaStream?.getTracks().forEach((track) => track.stop());
    this.mediaRecorder = undefined;
    this.mediaStream = undefined;
  }

  notifySpeechDetected(): void {
    this.options.onSpeechDetected?.();
  }

  private async blobToBase64(blob: Blob): Promise<string> {
    const buffer = await blob.arrayBuffer();
    let binary = "";
    const bytes = new Uint8Array(buffer);
    for (const byte of bytes) {
      binary += String.fromCharCode(byte);
    }
    return btoa(binary);
  }
}


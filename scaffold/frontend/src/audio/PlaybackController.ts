import type { TtsAudioEvent } from "../types/voice-events";

export class PlaybackController {
  private queue: TtsAudioEvent[] = [];
  private currentAudio?: HTMLAudioElement;
  private playing = false;

  enqueue(event: TtsAudioEvent): void {
    this.queue.push(event);
    void this.playNext();
  }

  stopAndClear(): void {
    this.queue = [];
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.src = "";
      this.currentAudio = undefined;
    }
    this.playing = false;
  }

  private async playNext(): Promise<void> {
    if (this.playing) return;
    const next = this.queue.shift();
    if (!next) return;

    this.playing = true;
    try {
      const audio = new Audio(this.toDataUrl(next));
      this.currentAudio = audio;
      await audio.play();
      await new Promise<void>((resolve) => {
        audio.onended = () => resolve();
        audio.onerror = () => resolve();
      });
    } finally {
      this.currentAudio = undefined;
      this.playing = false;
      void this.playNext();
    }
  }

  private toDataUrl(event: TtsAudioEvent): string {
    const mimeType = event.codec === "mp3" ? "audio/mpeg" : "audio/wav";
    return `data:${mimeType};base64,${event.audio_base64}`;
  }
}


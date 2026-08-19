import type {
  ClientVoiceEvent,
  ControlInterruptEvent,
  ServerVoiceEvent,
} from "../types/voice-events";

export interface VoiceSocketClientOptions {
  url: string;
  sessionId: string;
  onEvent: (event: ServerVoiceEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

export class VoiceSocketClient {
  private socket?: WebSocket;

  constructor(private readonly options: VoiceSocketClientOptions) {}

  connect(): void {
    this.socket = new WebSocket(this.options.url);
    this.socket.onopen = () => this.options.onOpen?.();
    this.socket.onclose = () => this.options.onClose?.();
    this.socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as ServerVoiceEvent;
      this.options.onEvent(event);
    };
  }

  send(event: ClientVoiceEvent): void {
    if (this.socket?.readyState !== WebSocket.OPEN) return;
    this.socket.send(JSON.stringify(event));
  }

  interrupt(
    reason: ControlInterruptEvent["reason"],
    turnId?: string,
  ): void {
    this.send({
      type: "control.interrupt",
      session_id: this.options.sessionId,
      timestamp_ms: Date.now(),
      turn_id: turnId,
      reason,
    });
  }

  close(): void {
    this.socket?.close();
    this.socket = undefined;
  }
}


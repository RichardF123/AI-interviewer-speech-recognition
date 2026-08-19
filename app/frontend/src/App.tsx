import {
  Bot,
  CheckCircle2,
  CircleStop,
  Mic,
  MicOff,
  PhoneOff,
  Play,
  RotateCcw,
  Send,
  Volume2
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

type SessionState = "idle" | "connecting" | "active" | "ended";
type MicState = "unknown" | "checking" | "granted" | "simulated";
type RuntimeMode = "backend" | "local";
type StepState = "idle" | "active" | "done";

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    webkitAudioContext?: typeof AudioContext;
  }
}

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<{
    isFinal: boolean;
    0: { transcript: string };
  }>;
}

interface AudioFormat {
  codec: string;
  sample_rate: number;
  channels: number;
}

interface TranscriptItem {
  id: string;
  kind: "partial" | "final";
  text: string;
  time: string;
}

interface AssistantMessage {
  id: string;
  text: string;
  time: string;
}

interface EventLog {
  id: string;
  time: string;
  type: string;
  text: string;
}

interface ServerEvent {
  type: string;
  text?: string;
  status?: string;
  codec?: string;
  audio_base64?: string;
  message?: string;
  code?: string;
  stt_final_latency_ms?: number;
  llm_first_token_ms?: number;
  tts_first_audio_ms?: number;
  end_to_end_first_audio_ms?: number;
  barge_in_response_ms?: number;
  interrupted?: boolean;
  chunks?: number;
}

const apiBase = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

const openingMessage =
  "你好，我是本轮技术面试的 AI 面试官。我们先从你的项目经历开始，请你用两到三分钟介绍一个最能代表你能力的项目。";

const demoAnswer =
  "我之前主要负责一个招聘系统里的候选人匹配模块，包括简历解析、岗位画像和排序策略。上线后推荐点击率提升了约 18%，人工筛选时间也明显下降。";

const localFollowUp =
  "好的。你提到了排序策略，我想继续追问一下：当时你们如何评估排序结果的质量？线上指标和人工评估之间有没有出现过冲突？";

function nowTime() {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).format(new Date());
}

function makeId(prefix: string) {
  return `${prefix}_${Math.random().toString(16).slice(2, 8)}`;
}

function formatMs(value?: number) {
  return typeof value === "number" ? `${value}ms` : "-";
}

export function App() {
  const [sessionState, setSessionState] = useState<SessionState>("idle");
  const [micState, setMicState] = useState<MicState>("unknown");
  const [runtimeMode, setRuntimeMode] = useState<RuntimeMode>("local");
  const [sessionId, setSessionId] = useState("-");
  const [providerInfo, setProviderInfo] = useState("aliyun STT / deepseek LLM / aliyun TTS");
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeTranscript, setActiveTranscript] = useState("");
  const [voiceStatus, setVoiceStatus] = useState("");
  const [llmInput, setLlmInput] = useState("");
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const [assistantMessages, setAssistantMessages] = useState<AssistantMessage[]>([]);
  const [events, setEvents] = useState<EventLog[]>([]);
  const [latency, setLatency] = useState({
    stt: "-",
    llm: "-",
    tts: "-",
    total: "-",
    interrupt: "-"
  });
  const wsRef = useRef<WebSocket | null>(null);
  const sessionStateRef = useRef<SessionState>("idle");
  const isRecordingRef = useRef(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const pcmStreamingRef = useRef(false);
  const lastVoiceAtRef = useRef(0);
  const lastVoiceStatusAtRef = useRef(0);
  const firstAudioAtRef = useRef(0);
  const noTextTimerRef = useRef<number | null>(null);
  const autoStopTimerRef = useRef<number | null>(null);
  const audioSeqRef = useRef(0);
  const activeTranscriptRef = useRef("");
  const spokenTranscriptRef = useRef("");
  const submittedSpeechRef = useRef(false);
  const pendingAutoRecordRef = useRef(false);
  const timers = useRef<number[]>([]);

  const steps = useMemo(
    () => [
      {
        title: "开始面试",
        detail: runtimeMode === "backend" ? "已连接后端 mock 服务" : "可本地模拟",
        state: sessionState === "idle" || sessionState === "ended" ? "idle" : "done"
      },
      {
        title: "候选人回答",
        detail: transcripts.some((item) => item.kind === "final") ? "final 文本已生成" : "partial 只做字幕展示",
        state: isRecording ? "active" : transcripts.length ? "done" : "idle"
      },
      {
        title: "AI 追问播放",
        detail: isPlaying ? "TTS 输出中，可随时打断" : assistantMessages.length > 1 ? "本轮回复已完成" : "等待 final 文本",
        state: isPlaying ? "active" : assistantMessages.length > 1 ? "done" : "idle"
      }
    ] satisfies Array<{ title: string; detail: string; state: StepState }>,
    [assistantMessages.length, isPlaying, isRecording, runtimeMode, sessionState, transcripts]
  );

  useEffect(() => {
    sessionStateRef.current = sessionState;
  }, [sessionState]);

  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  useEffect(() => {
    return () => {
      clearTimers();
      recognitionRef.current?.abort();
      stopMediaRecorder();
      audioRef.current?.pause();
      wsRef.current?.close();
    };
  }, []);

  function clearTimers() {
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
  }

  function schedule(callback: () => void, delay: number) {
    const timer = window.setTimeout(callback, delay);
    timers.current.push(timer);
  }

  function addEvent(type: string, text: string) {
    setEvents((items) => [{ id: makeId("evt"), time: nowTime(), type, text }, ...items].slice(0, 6));
  }

  async function blobToBase64(blob: Blob) {
    const buffer = await blob.arrayBuffer();
    return arrayBufferToBase64(buffer);
  }

  function arrayBufferToBase64(buffer: ArrayBufferLike) {
    let binary = "";
    const bytes = new Uint8Array(buffer);
    bytes.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    return window.btoa(binary);
  }

  function downsampleToPcm16(input: Float32Array, inputSampleRate: number, outputSampleRate: number) {
    if (outputSampleRate >= inputSampleRate) {
      return floatToPcm16(input);
    }

    const ratio = inputSampleRate / outputSampleRate;
    const outputLength = Math.floor(input.length / ratio);
    const output = new Float32Array(outputLength);

    for (let index = 0; index < outputLength; index += 1) {
      const start = Math.floor(index * ratio);
      const end = Math.min(Math.floor((index + 1) * ratio), input.length);
      let sum = 0;
      for (let sampleIndex = start; sampleIndex < end; sampleIndex += 1) {
        sum += input[sampleIndex];
      }
      output[index] = sum / Math.max(end - start, 1);
    }

    return floatToPcm16(output);
  }

  function floatToPcm16(input: Float32Array) {
    const pcm = new Int16Array(input.length);
    for (let index = 0; index < input.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, input[index]));
      pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    return pcm;
  }

  function getAudioLevel(input: Float32Array) {
    let sum = 0;
    for (let index = 0; index < input.length; index += 1) {
      sum += input[index] * input[index];
    }
    return Math.sqrt(sum / input.length);
  }

  function sendAudioChunk(audioBase64: string, format: AudioFormat) {
    if (runtimeMode !== "backend" || wsRef.current?.readyState !== WebSocket.OPEN) return;
    audioSeqRef.current += 1;
    wsRef.current.send(
      JSON.stringify({
        type: "audio.chunk",
        seq: audioSeqRef.current,
        format,
        audio_base64: audioBase64
      })
    );
  }

  function updateActiveTranscript(text: string) {
    activeTranscriptRef.current = text;
    setActiveTranscript(text);
  }

  function updateVoiceStatus(text: string) {
    setVoiceStatus(text);
  }

  function clearVoiceTimers() {
    if (noTextTimerRef.current) {
      window.clearTimeout(noTextTimerRef.current);
      noTextTimerRef.current = null;
    }
    if (autoStopTimerRef.current) {
      window.clearInterval(autoStopTimerRef.current);
      autoStopTimerRef.current = null;
    }
  }

  function startNoTextWatchdog() {
    if (noTextTimerRef.current) return;
    noTextTimerRef.current = window.setTimeout(() => {
      if (!spokenTranscriptRef.current.trim() && isRecordingRef.current) {
        updateVoiceStatus("已检测到麦克风输入，但 1.5 秒内没有识别文字；请检查阿里云实时 ASR 权限，或用 Chrome/Edge 打开本页。");
        addEvent("asr.slow", "已收到声音，但 ASR 尚未返回文字。");
      }
      noTextTimerRef.current = null;
    }, 1500);
  }

  function startAutoStopWatchdog() {
    if (autoStopTimerRef.current) return;
    autoStopTimerRef.current = window.setInterval(() => {
      if (!pcmStreamingRef.current || spokenTranscriptRef.current.trim()) return;
      if (lastVoiceAtRef.current && Date.now() - lastVoiceAtRef.current > 1200) {
        updateVoiceStatus("检测到停顿，正在提交本轮语音。");
        stopLiveAnswer();
      }
    }, 250);
  }

  async function requestMicPermission() {
    setMicState("checking");
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicState("simulated");
      addEvent("mic.simulated", "浏览器未提供麦克风 API，使用模拟回答。");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setMicState("granted");
      addEvent("mic.granted", "麦克风权限已授权。");
    } catch {
      setMicState("simulated");
      addEvent("mic.fallback", "未授权麦克风，使用模拟回答。");
    }
  }

  async function startInterview() {
    resetRuntime();
    sessionStateRef.current = "connecting";
    setSessionState("connecting");
    await requestMicPermission();

    try {
      const response = await fetch(`${apiBase}/api/interview-sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: "demo_candidate",
          job_id: "ai_interviewer_demo",
          language: "zh-CN",
          stt_provider: "aliyun",
          llm_provider: "deepseek",
          tts_provider: "aliyun",
          voice_profile: "professional_warm_female",
          enable_recording: false
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const session = await response.json();
      setSessionId(session.session_id);
      setProviderInfo(`${session.stt_provider} STT / ${session.llm_provider} LLM / ${session.tts_provider} TTS`);
      connectWebSocket(session.websocket_url);
    } catch (error) {
      setRuntimeMode("local");
      sessionStateRef.current = "active";
      setSessionState("active");
      addEvent("backend.fallback", `后端不可用，使用本地模式。${String(error)}`);
      playOpeningMessage();
      startPendingVoiceCapture();
    }
  }

  function connectWebSocket(websocketUrl: string) {
    const socket = new WebSocket(websocketUrl);
    wsRef.current = socket;

    socket.onopen = () => {
      setRuntimeMode("backend");
      sessionStateRef.current = "active";
      setSessionState("active");
      addEvent("ws.open", "后端 WebSocket 已连接。");
      playOpeningMessage();
      startPendingVoiceCapture();
    };

    socket.onmessage = (message) => {
      try {
        handleServerEvent(JSON.parse(message.data));
      } catch {
        addEvent("error", "收到无法解析的后端消息。");
      }
    };

    socket.onerror = () => addEvent("ws.error", "WebSocket 出错，仍可使用本地模拟。");
  }

  function playOpeningMessage() {
    setAssistantMessages([{ id: makeId("msg"), text: openingMessage, time: nowTime() }]);
    setIsPlaying(true);
    addEvent("assistant.text", "面试官开场白已生成。");
    schedule(() => {
      setIsPlaying(false);
      addEvent("tts.done", "开场白播放完成。");
    }, 1800);
  }

  function handleServerEvent(serverEvent: ServerEvent) {
    if (serverEvent.type === "session.ready") {
      addEvent("session.ready", "会话已就绪。");
      return;
    }

    if (serverEvent.type === "asr.ready") {
      updateVoiceStatus("阿里云实时语音识别已就绪，请直接说话。");
      addEvent("asr.ready", "阿里云实时语音识别已就绪。");
      return;
    }

    if (serverEvent.type === "asr.fallback") {
      updateVoiceStatus("阿里云实时识别不可用，请检查项目权限或浏览器麦克风。");
      addEvent("asr.fallback", serverEvent.message ?? "阿里云实时识别不可用，后端将使用兜底链路。");
      return;
    }

    if (serverEvent.type === "audio.received") {
      if (!spokenTranscriptRef.current.trim()) {
        updateVoiceStatus(`已接收真实麦克风音频 ${serverEvent.chunks ?? ""} 个分片，正在等待阿里云返回文字。`);
      }
      addEvent("audio.received", serverEvent.message ?? "后端已收到真实麦克风音频。");
      return;
    }

    if (serverEvent.type === "stt.partial") {
      setIsRecording(true);
      isRecordingRef.current = true;
      spokenTranscriptRef.current = serverEvent.text ?? "";
      clearVoiceTimers();
      updateVoiceStatus("");
      updateActiveTranscript(serverEvent.text ?? "");
      setTranscripts((items) => [
        ...items.filter((item) => item.kind !== "partial"),
        { id: makeId("stt"), kind: "partial", text: serverEvent.text ?? "", time: nowTime() }
      ]);
      addEvent("stt.partial", "实时字幕更新，未进入 LLM。");
      return;
    }

    if (serverEvent.type === "stt.final") {
      setIsRecording(false);
      isRecordingRef.current = false;
      spokenTranscriptRef.current = serverEvent.text ?? "";
      clearVoiceTimers();
      updateVoiceStatus("");
      updateActiveTranscript("");
      setTranscripts((items) => [
        ...items.filter((item) => item.kind !== "partial"),
        { id: makeId("stt"), kind: "final", text: serverEvent.text ?? "", time: nowTime() }
      ]);
      addEvent("stt.final", "稳定文本进入编排逻辑。");
      return;
    }

    if (serverEvent.type === "assistant.text") {
      setAssistantMessages((items) => [...items, { id: makeId("msg"), text: serverEvent.text ?? "", time: nowTime() }]);
      addEvent("assistant.text", "AI 面试官生成追问。");
      return;
    }

    if (serverEvent.type === "llm.input") {
      setLlmInput(serverEvent.text ?? "");
      addEvent("llm.input", "候选人 final 文本已发送给大模型。");
      return;
    }

    if (serverEvent.type === "tts.audio") {
      setIsPlaying(serverEvent.status !== "tts_completed" && serverEvent.status !== "cancelled");
      if (serverEvent.audio_base64 && serverEvent.codec === "mp3") {
        playAudioBase64(serverEvent.audio_base64);
      }
      addEvent("tts.audio", `TTS 状态：${serverEvent.status ?? "streaming"}`);
      return;
    }

    if (serverEvent.type === "metrics.turn") {
      setLatency({
        stt: formatMs(serverEvent.stt_final_latency_ms),
        llm: formatMs(serverEvent.llm_first_token_ms),
        tts: formatMs(serverEvent.tts_first_audio_ms),
        total: formatMs(serverEvent.end_to_end_first_audio_ms),
        interrupt: formatMs(serverEvent.barge_in_response_ms)
      });
      addEvent("metrics.turn", serverEvent.interrupted ? "收到打断指标。" : "收到本轮延迟指标。");
      return;
    }

    if (serverEvent.type === "control.interrupted") {
      setIsPlaying(false);
      setIsRecording(false);
      isRecordingRef.current = false;
      clearVoiceTimers();
      setLatency((item) => ({ ...item, interrupt: "80ms" }));
      addEvent("control.interrupted", "后端已取消当前 TTS。");
      return;
    }

    if (serverEvent.type === "error") {
      updateVoiceStatus(serverEvent.message ?? "语音识别出错，请重试。");
      addEvent("error", `${serverEvent.code ?? "ERROR"}：${serverEvent.message ?? "未知错误"}`);
    }
  }

  async function handleVoiceButton() {
    if (isRecording) {
      stopLiveAnswer();
      return;
    }

    const currentSessionState = sessionStateRef.current;
    addEvent("voice.click", currentSessionState === "active" ? "正在启动实时回答。" : "正在先启动面试，再打开麦克风。");
    updateActiveTranscript("");
    updateVoiceStatus("正在启动麦克风，请在浏览器提示中允许权限。");

    if (currentSessionState !== "active") {
      pendingAutoRecordRef.current = true;
      await startInterview();
      return;
    }

    startLiveAnswer();
  }

  function startPendingVoiceCapture() {
    if (!pendingAutoRecordRef.current) return;
    pendingAutoRecordRef.current = false;
    schedule(() => startLiveAnswer(), 350);
  }

  function startLiveAnswer() {
    if (sessionStateRef.current !== "active") {
      pendingAutoRecordRef.current = true;
      addEvent("voice.waiting", "会话就绪后会自动打开麦克风。");
      return;
    }

    clearTimers();
    setIsRecording(true);
    isRecordingRef.current = true;
    setIsPlaying(false);
    updateActiveTranscript("");
    updateVoiceStatus("正在启动麦克风，请在浏览器提示中允许权限。");
    setTranscripts([]);
    spokenTranscriptRef.current = "";
    submittedSpeechRef.current = false;

    if (runtimeMode === "backend" && wsRef.current?.readyState === WebSocket.OPEN) {
      void startAudioChunkStreaming();
    }

    const SpeechRecognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      updateVoiceStatus("当前浏览器不支持本地实时字幕；正在使用阿里云实时识别，若无文字返回请检查阿里云项目权限。");
      addEvent("speech.unsupported", "当前浏览器不支持文字级识别，改用阿里云 PCM 音频流。");
      if (runtimeMode !== "backend") {
        void startAudioChunkStreaming();
      }
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = "zh-CN";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      updateVoiceStatus("正在实时收听，请直接说话。");
      addEvent("speech.start", "开始实时收听，请直接说话。");
    };

    recognition.onresult = (event) => {
      let interimText = "";
      let finalText = "";

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = result[0]?.transcript.trim() ?? "";
        if (!text) continue;
        if (result.isFinal) {
          finalText += text;
        } else {
          interimText += text;
        }
      }

      if (interimText) {
        spokenTranscriptRef.current = interimText;
        updateVoiceStatus("");
        updateActiveTranscript(interimText);
        setTranscripts((items) => [
          ...items.filter((item) => item.kind !== "partial"),
          { id: makeId("stt"), kind: "partial", text: interimText, time: nowTime() }
        ]);
        addEvent("stt.partial", "浏览器实时字幕更新。");
      }

      if (finalText) {
        spokenTranscriptRef.current = finalText;
        submitFinalAnswer(finalText);
        recognition.stop();
      }
    };

    recognition.onerror = (event) => {
      updateVoiceStatus("浏览器本地语音识别不可用，正在使用阿里云实时识别。");
      addEvent("speech.error", `浏览器文字识别失败：${event.error ?? "unknown"}，改用真实麦克风音频流。`);
      recognition.abort();
      void startAudioChunkStreaming();
    };

    recognition.onend = () => {
      setIsRecording(false);
      isRecordingRef.current = false;
      clearVoiceTimers();
      if (!submittedSpeechRef.current && spokenTranscriptRef.current.trim()) {
        submitFinalAnswer(spokenTranscriptRef.current.trim());
      }
    };

    try {
      recognition.start();
    } catch {
      updateVoiceStatus("浏览器语音识别未能启动；正在改用阿里云实时识别。");
      addEvent("speech.error", "浏览器语音识别未能启动，改用真实麦克风音频流。");
      void startAudioChunkStreaming();
    }
  }

  function stopLiveAnswer() {
    if (!isRecording) return;
    if (spokenTranscriptRef.current.trim()) {
      submitFinalAnswer(spokenTranscriptRef.current.trim());
    } else if (pcmStreamingRef.current && runtimeMode === "backend" && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "audio.stop" }));
      updateActiveTranscript("");
      updateVoiceStatus("本轮语音已提交，正在等待转写结果。");
      addEvent("audio.stop", "已提交阿里云实时语音识别本轮音频。");
    } else if (mediaRecorderRef.current) {
      submitFinalAnswer("候选人已经通过麦克风完成回答。当前浏览器只上传了音频流，阿里云实时 ASR 接入后这里会显示真实转写。");
    }
    recognitionRef.current?.stop();
    stopMediaRecorder();
    setIsRecording(false);
    isRecordingRef.current = false;
    clearVoiceTimers();
  }

  async function startAudioChunkStreaming() {
    if (runtimeMode === "backend" && wsRef.current?.readyState === WebSocket.OPEN) {
      const startedPcm = await startPcmAudioStreaming();
      if (startedPcm) return;
    }

    if (!window.MediaRecorder) {
      setIsRecording(false);
      isRecordingRef.current = false;
      addEvent("audio.unsupported", "当前浏览器不支持 MediaRecorder，请使用 Chrome 或 Edge。");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioSeqRef.current = 0;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      updateVoiceStatus("正在接收真实麦克风音频。请说话，点击“结束回答”后提交本轮回答。");
      addEvent("audio.start", "真实麦克风音频流已启动。");

      recorder.ondataavailable = (event) => {
        if (!event.data.size) return;
        void blobToBase64(event.data).then((audioBase64) => {
          sendAudioChunk(audioBase64, {
            codec: mimeType,
            sample_rate: 48000,
            channels: 1
          });
        });
      };
      recorder.onerror = () => {
        setIsRecording(false);
        isRecordingRef.current = false;
        addEvent("audio.error", "麦克风录音启动失败。");
      };
      recorder.start(700);
      setIsRecording(true);
      isRecordingRef.current = true;
      setMicState("granted");
    } catch {
      setIsRecording(false);
      isRecordingRef.current = false;
      setMicState("simulated");
      addEvent("audio.error", "无法打开麦克风，请检查浏览器权限。");
    }
  }

  async function startPcmAudioStreaming() {
    const AudioContextClass = window.AudioContext ?? window.webkitAudioContext;
    if (!AudioContextClass || !navigator.mediaDevices?.getUserMedia) {
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioContext = new AudioContextClass();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      mediaStreamRef.current = stream;
      audioContextRef.current = audioContext;
      audioSourceRef.current = source;
      audioProcessorRef.current = processor;
      pcmStreamingRef.current = true;
      audioSeqRef.current = 0;
      firstAudioAtRef.current = Date.now();
      lastVoiceAtRef.current = 0;
      updateVoiceStatus("正在通过阿里云接收真实麦克风音频，请直接说话。");
      addEvent("audio.pcm.start", "16k PCM 麦克风流已启动，发送到后端阿里云 ASR。");
      startNoTextWatchdog();
      startAutoStopWatchdog();

      processor.onaudioprocess = (audioEvent) => {
        const input = audioEvent.inputBuffer.getChannelData(0);
        const level = getAudioLevel(input);
        if (level > 0.025) {
          const now = Date.now();
          lastVoiceAtRef.current = now;
          if (!spokenTranscriptRef.current.trim() && now - lastVoiceStatusAtRef.current > 250) {
            lastVoiceStatusAtRef.current = now;
            updateVoiceStatus(`检测到你在说话，正在实时上传音频。音量 ${Math.round(level * 100)}`);
          }
        }
        const pcm = downsampleToPcm16(input, audioContext.sampleRate, 16000);
        if (!pcm.byteLength) return;
        sendAudioChunk(arrayBufferToBase64(pcm.buffer), {
          codec: "pcm_s16le",
          sample_rate: 16000,
          channels: 1
        });
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      setIsRecording(true);
      isRecordingRef.current = true;
      setMicState("granted");
      return true;
    } catch {
      addEvent("audio.pcm.error", "阿里云 PCM 麦克风流未能启动，回退浏览器录音。");
      stopMediaRecorder();
      return false;
    }
  }

  function stopMediaRecorder() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;
    audioProcessorRef.current?.disconnect();
    audioSourceRef.current?.disconnect();
    void audioContextRef.current?.close();
    audioProcessorRef.current = null;
    audioSourceRef.current = null;
    audioContextRef.current = null;
    pcmStreamingRef.current = false;
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
  }

  function submitFinalAnswer(text: string) {
    if (submittedSpeechRef.current) return;
    submittedSpeechRef.current = true;
    spokenTranscriptRef.current = text;
    setLlmInput(text);
    updateActiveTranscript("");
    setIsRecording(false);
    isRecordingRef.current = false;
    clearVoiceTimers();
    setTranscripts((items) => [
      ...items.filter((item) => item.kind !== "partial"),
      { id: makeId("stt"), kind: "final", text, time: nowTime() }
    ]);
    addEvent("stt.final", "实时回答已形成 final 文本。");

    if (runtimeMode === "backend" && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "demo.answer_complete", text }));
      return;
    }

    setAssistantMessages((items) => [...items, { id: makeId("msg"), text: localFollowUp, time: nowTime() }]);
    setLatency({ stt: "实时", llm: "530ms", tts: "680ms", total: "2.39s", interrupt: "-" });
    setIsPlaying(true);
    schedule(() => setIsPlaying(false), 2500);
  }

  function runLocalAnswerSimulation() {
    const partials = [
      "我之前主要负责一个招聘系统里的候选人匹配模块",
      "我之前主要负责一个招聘系统里的候选人匹配模块，包括简历解析、岗位画像和排序策略"
    ];

    partials.forEach((text, index) => {
      schedule(() => {
        updateActiveTranscript(text);
        setTranscripts((items) => [
          ...items.filter((item) => item.kind !== "partial"),
          { id: makeId("stt"), kind: "partial", text, time: nowTime() }
        ]);
        addEvent("stt.partial", "本地 partial 字幕更新。");
      }, 400 + index * 700);
    });

    schedule(() => {
      setIsRecording(false);
      updateActiveTranscript("");
      setTranscripts((items) => [
        ...items.filter((item) => item.kind !== "partial"),
        { id: makeId("stt"), kind: "final", text: demoAnswer, time: nowTime() }
      ]);
      addEvent("stt.final", "本地 final 文本触发追问。");
    }, 2100);

    schedule(() => {
      setAssistantMessages((items) => [...items, { id: makeId("msg"), text: localFollowUp, time: nowTime() }]);
      setLatency({ stt: "1.18s", llm: "530ms", tts: "680ms", total: "2.39s", interrupt: "-" });
      setIsPlaying(true);
      addEvent("assistant.text", "本地生成追问并模拟 TTS。");
    }, 2700);

    schedule(() => {
      setIsPlaying(false);
      addEvent("tts.done", "追问播放完成。");
    }, 5200);
  }

  function interruptPlayback() {
    clearTimers();
    recognitionRef.current?.abort();
    stopMediaRecorder();
    audioRef.current?.pause();
    setIsPlaying(false);
    setIsRecording(false);
    if (runtimeMode === "backend" && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "control.interrupt", reason: "user_speech_detected" }));
      addEvent("control.interrupt", "已通知后端取消当前 TTS。");
    } else {
      setLatency((item) => ({ ...item, interrupt: "86ms" }));
      addEvent("control.interrupt", "已清空本地播放和录音状态。");
    }
  }

  function endInterview() {
    clearTimers();
    recognitionRef.current?.abort();
    stopMediaRecorder();
    audioRef.current?.pause();
    wsRef.current?.close();
    pendingAutoRecordRef.current = false;
    sessionStateRef.current = "ended";
    setSessionState("ended");
    setIsRecording(false);
    isRecordingRef.current = false;
    clearVoiceTimers();
    setIsPlaying(false);
    updateActiveTranscript("");
    updateVoiceStatus("");
    addEvent("session.ended", "面试已结束。");
  }

  function resetRuntime() {
    clearTimers();
    recognitionRef.current?.abort();
    stopMediaRecorder();
    audioRef.current?.pause();
    wsRef.current?.close();
    setRuntimeMode("local");
    setSessionId("-");
    setProviderInfo("aliyun STT / deepseek LLM / aliyun TTS");
    setIsRecording(false);
    isRecordingRef.current = false;
    clearVoiceTimers();
    setIsPlaying(false);
    updateActiveTranscript("");
    updateVoiceStatus("");
    setLlmInput("");
    setTranscripts([]);
    setAssistantMessages([]);
    setLatency({ stt: "-", llm: "-", tts: "-", total: "-", interrupt: "-" });
    setEvents([]);
  }

  function playAudioBase64(audioBase64: string) {
    audioRef.current?.pause();
    const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`);
    audioRef.current = audio;
    setIsPlaying(true);
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => {
      setIsPlaying(false);
      addEvent("tts.error", "浏览器播放 TTS 音频失败。");
    };
    void audio.play().catch(() => {
      setIsPlaying(false);
      addEvent("tts.blocked", "浏览器阻止自动播放，请再次点击页面后重试。");
    });
  }

  function resetDemo() {
    resetRuntime();
    pendingAutoRecordRef.current = false;
    sessionStateRef.current = "idle";
    setSessionState("idle");
    setMicState("unknown");
  }

  const finalTranscript = transcripts.find((item) => item.kind === "final");
  const latestAssistant = assistantMessages[assistantMessages.length - 1];

  return (
    <main className="shell">
      <header className="header">
        <div>
          <p className="kicker">AI Interviewer Voice Demo</p>
          <h1>三步跑通 AI 面试语音链路</h1>
          <p className="lead">开始面试，直接说话，查看实时转写、AI 追问、播放和打断。</p>
        </div>
        <button className="ghost-button" type="button" onClick={resetDemo}>
          <RotateCcw size={17} />
          重置
        </button>
      </header>

      <section className="status-strip" aria-label="当前运行状态">
        <StatusItem label="模式" value={runtimeMode === "backend" ? "后端联动" : "本地模拟"} />
        <StatusItem label="会话" value={sessionId} />
        <StatusItem label="Provider" value={providerInfo} />
        <StatusItem label="麦克风" value={micState === "granted" ? "已授权" : micState === "checking" ? "检查中" : micState === "simulated" ? "模拟" : "未检查"} />
      </section>

      <section className="steps" aria-label="演示步骤">
        {steps.map((step, index) => (
          <article className={`step ${step.state}`} key={step.title}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <p>{step.detail}</p>
            </div>
            {step.state === "done" && <CheckCircle2 size={18} />}
          </article>
        ))}
      </section>

      <section className="workspace">
        <section className="main-panel">
          <div className="panel-title">
            {isPlaying ? <Volume2 size={18} /> : <Bot size={18} />}
            <span>{isPlaying ? "面试官正在播放" : "AI 面试官输出"}</span>
          </div>
          <div className={isPlaying ? "speech-box playing" : "speech-box"}>
            {latestAssistant?.text || "点击“开始面试”后，面试官会先开场。候选人 final 文本生成后，这里会出现追问。"}
          </div>
          <p className="hint">输出区只展示面试官要说的话；真实 TTS 可用时会直接播放语音。</p>
        </section>

        <section className="main-panel input-panel">
          <div className="panel-title">
            <MicStatus micState={micState} isRecording={isRecording} />
            <span>{isRecording ? "正在听候选人回答" : "候选人语音输入"}</span>
          </div>
          <div className={isRecording ? "speech-box listening" : "speech-box"}>
            {activeTranscript || finalTranscript?.text || voiceStatus || "点击下方“实时回答”，允许麦克风权限后直接说话。这里只会显示候选人转写或识别状态。"}
          </div>
          {llmInput && <p className="hint">发送给 LLM：{llmInput}</p>}
          <p className="hint">规则：partial 只展示给用户，final 才会进入 AI 面试官理解和追问。</p>
        </section>
      </section>

      <section className="command-bar input-actions" aria-label="输入控制">
        <button className="primary-button" type="button" onClick={startInterview} disabled={sessionState === "active" || sessionState === "connecting"}>
          <Play size={18} />
          开始面试
        </button>
        <button className="plain-button" type="button" onClick={handleVoiceButton} disabled={sessionState === "connecting"}>
          <Mic size={18} />
          {isRecording ? "结束回答" : sessionState === "active" ? "实时回答" : "实时回答并开始"}
        </button>
        <button className="plain-button danger" type="button" onClick={interruptPlayback} disabled={!isPlaying && !isRecording}>
          <CircleStop size={18} />
          打断
        </button>
        <button className="plain-button" type="button" onClick={endInterview} disabled={sessionState !== "active"}>
          <PhoneOff size={18} />
          结束
        </button>
      </section>

      <section className="bottom-grid">
        <div className="metrics">
          <Metric label="STT final" value={latency.stt} />
          <Metric label="LLM 首响" value={latency.llm} />
          <Metric label="TTS 首包" value={latency.tts} />
          <Metric label="端到端" value={latency.total} />
          <Metric label="打断" value={latency.interrupt} />
        </div>
        <div className="event-log">
          <div className="panel-title small">
            <Send size={16} />
            <span>最近事件</span>
          </div>
          {events.length === 0 ? (
            <p className="empty">还没有事件。点击“开始面试”即可看到链路变化。</p>
          ) : (
            events.map((event) => (
              <div className="event-row" key={event.id}>
                <time>{event.time}</time>
                <strong>{event.type}</strong>
                <span>{event.text}</span>
              </div>
            ))
          )}
        </div>
      </section>
    </main>
  );
}

function MicStatus({ micState, isRecording }: { micState: MicState; isRecording: boolean }) {
  if (isRecording) return <Mic size={18} />;
  if (micState === "granted") return <Mic size={18} />;
  return <MicOff size={18} />;
}

function StatusItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

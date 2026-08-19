# AI Interviewer Voice Frontend

React + Vite + TypeScript 前端，用于演示电话式 AI 面试语音链路。

## 运行

```powershell
cd app/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5185
```

访问：

```text
http://127.0.0.1:5185/
```

默认后端：

```text
http://127.0.0.1:8011
```

可通过 `VITE_API_BASE` 覆盖。

## 当前交互

- 点击一次“开始面试”。
- 页面播放 AI 面试官开场白。
- 开场白结束后自动进入聆听。
- 候选人直接说话，不需要点击录音按钮。
- 浏览器 `SpeechRecognition` 可用时，实时显示 partial/final 字幕。
- final 文本通过 `speech.final` 发送给后端 DeepSeek。
- AI 输出文字立刻展示，并用浏览器 TTS 自动读出。
- 阿里云 TTS 返回 mp3 时也可播放真实音频。
- “静音 / 恢复聆听”用于电话式控制。
- “打断”会取消当前播放和后端 TTS 状态。

## 浏览器要求

推荐使用 Chrome 或 Edge。

原因：

- Codex 内置浏览器或部分 WebView 可能不支持 `SpeechRecognition`。
- 如果浏览器实时字幕不可用，页面会退到后端实时 ASR；若阿里云 ASR 也不可用，就无法做到说话马上显示文字。

## 前端职责

- 麦克风权限和音频采集。
- 音量/VAD 级别的即时状态反馈。
- 实时字幕展示。
- final 文本提交。
- AI 文字输出展示。
- 浏览器 TTS 兜底播放。
- 多轮自动恢复聆听。

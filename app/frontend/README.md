# AI 面试官语音控制台 Demo

这是一个独立的 Vite + React + TypeScript 前端展示应用，用 mock 事件模拟 AI 面试官语音链路。

## 功能

- 开始/结束面试
- 麦克风权限状态提示
- 模拟录音状态
- 候选人 `partial/final` 实时转写
- AI 面试官文本回复
- TTS 播放状态
- `barge-in` 打断按钮
- STT、LLM、TTS、播放链路状态面板
- turn 级延迟指标面板
- 事件日志

## 运行

```bash
cd app/frontend
npm install
npm run dev
```

浏览器打开终端显示的本地地址，通常是 `http://localhost:5173/`。

## 说明

当前版本不依赖后端，也不会调用真实 STT/TTS/LLM 服务。后续接入真实服务时，可将 mock 事件替换为 `/ws/voice/session` WebSocket 事件流。

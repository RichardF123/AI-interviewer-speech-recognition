# 前端骨架

本目录是 AI 面试官语音功能的前端 TypeScript 骨架，适合放入 Next.js 项目继续开发。

## 模块

- `src/audio/AudioCaptureClient.ts`：麦克风采集和音频 chunk 回调。
- `src/audio/PlaybackController.ts`：TTS 音频播放队列和打断停止。
- `src/ws/VoiceSocketClient.ts`：WebSocket 事件收发、重连和打断。
- `src/types/voice-events.ts`：前后端共享事件类型。

## 需要补齐

- UI 页面和权限提示。
- `AudioWorklet` PCM16 转换实现。
- 真实音频解码和浏览器兼容处理。
- 自动 VAD 或音量阈值检测。
- 与后端鉴权 token 获取逻辑。

当前实现只提供工程边界，不代表完整生产代码。


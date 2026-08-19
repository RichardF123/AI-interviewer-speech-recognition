# AI 面试官语音功能开发骨架

本目录提供前后端开发骨架，用于研发评审、任务拆分和后续实现。当前代码包含 mock provider 和接口占位，不包含真实云服务接入，也不包含任何真实 API Key、Secret 或 Token。

## 目录

- `frontend/`：Next.js/TypeScript 侧的录音、WebSocket、播放和打断控制骨架。
- `backend/`：FastAPI 侧的 REST、WebSocket、STT/TTS provider、编排和日志骨架。

## 默认运行思路

1. 前端采集麦克风音频，发送 `audio.chunk`。
2. 后端 mock STT 产生 `stt.partial` 和 `stt.final`。
3. `stt.final` 进入 orchestrator。
4. orchestrator 生成面试官文本。
5. mock TTS 输出 `tts.audio` 占位事件。
6. 前端播放队列接收音频事件，支持 `control.interrupt`。

## 生产接入前必须补齐

- Azure Speech SDK 或其他 STT provider 的真实实现。
- Azure Neural TTS 或其他 TTS provider 的真实实现。
- LLM provider 调用与 prompt 管理。
- 数据库、对象存储、鉴权、审计和加密。
- 候选人授权与数据删除流程。


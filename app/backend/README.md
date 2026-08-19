# AI 面试官语音后端 Mock Demo

这是一个用于前端联调的 FastAPI 后端 Mock 服务，模拟 AI 面试官语音链路：

候选人音频事件 -> mock STT partial/final -> mock LLM 面试官回复 -> mock TTS 音频状态 -> turn 指标。

当前实现不接入真实 Azure、腾讯云、阿里云或 OpenAI 服务，也不需要真实 API Key。

## 启动方式

```powershell
cd app/backend
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 创建面试会话

```http
POST http://127.0.0.1:8000/api/interview-sessions
Content-Type: application/json
```

请求示例：

```json
{
  "candidate_id": "candidate_demo",
  "job_id": "backend_engineer",
  "language": "zh-CN",
  "stt_provider": "mock",
  "tts_provider": "mock",
  "voice_profile": "professional_warm_female"
}
```

响应会返回 `session_id` 和 `websocket_url`。

## WebSocket

连接：

```text
ws://127.0.0.1:8000/ws/voice/session?session_id=<session_id>
```

客户端可发送事件：

- `audio.chunk`：模拟音频分片，服务端会返回 `stt.partial`。
- `demo.answer_start`：模拟候选人开始回答。
- `demo.answer_complete`：模拟候选人回答结束，服务端会返回 `stt.final`，然后触发 mock LLM 和 mock TTS。
- `control.interrupt`：模拟候选人打断，会取消或标记当前 TTS 播放。

重要规则：

- `stt.partial` 只用于前端字幕展示，不进入 LLM。
- 只有 `stt.final` 会触发 orchestrator。
- `control.interrupt` 会取消当前 TTS 任务，并返回打断确认与指标。


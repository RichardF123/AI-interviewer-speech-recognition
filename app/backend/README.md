# AI Interviewer Voice Backend

FastAPI 后端，负责语音会话、WebSocket 事件、ASR/LLM/TTS provider 调度。

## 运行

```powershell
cd app/backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

## 核心接口

```http
GET /health
GET /api/provider-status
POST /api/interview-sessions
WS /ws/voice/session?session_id=<session_id>
```

创建会话示例：

```json
{
  "candidate_id": "demo_candidate",
  "job_id": "ai_interviewer_demo",
  "language": "zh-CN",
  "stt_provider": "aliyun",
  "llm_provider": "deepseek",
  "tts_provider": "aliyun",
  "voice_profile": "professional_warm_female"
}
```

## WebSocket 事件

客户端到服务端：

- `audio.chunk`：16k PCM 音频分片，用于后端实时 ASR 或分段 ASR。
- `audio.stop`：结束当前音频段。
- `speech.final`：前端已经拿到稳定候选人文本，直接进入 LLM 链路。
- `control.interrupt`：用户打断 AI 播放。

服务端到客户端：

- `session.ready`
- `asr.starting`
- `asr.ready`
- `asr.fallback`
- `audio.received`
- `stt.partial`
- `stt.final`
- `llm.input`
- `assistant.text`
- `tts.audio`
- `metrics.turn`
- `control.interrupted`
- `error`

关键规则：

- `partial` 只展示，不进入 LLM。
- `final` 才进入 DeepSeek。
- 多轮输入采用最新 final 优先，上一轮未完成 LLM 任务会被取消。
- 系统状态文本不会作为候选人回答进入 LLM。

## Provider

LLM：

- `deepseek`
- 配置：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`

ASR：

- `aliyun`：实时 ASR 主链路，目标返回 `stt.partial` / `stt.final`
- `mimo`：分段 ASR 备份，`supports_partial=false`

TTS：

- `aliyun`：阿里云 REST TTS 返回 mp3
- 前端浏览器 TTS 会作为兜底，保证本地 demo 能听到回复

## 注意

`.env` 只放本地真实密钥，不提交。`.env.example` 只维护变量名和默认 endpoint。

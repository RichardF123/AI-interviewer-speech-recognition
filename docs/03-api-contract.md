# API 契约

## 创建面试会话

`POST /api/interview-sessions`

请求示例：

```json
{
  "candidate_id": "c_123",
  "job_id": "backend_java_mid",
  "language": "zh-CN",
  "stt_provider": "azure",
  "tts_provider": "azure",
  "voice_profile": "professional_warm_female",
  "enable_recording": true,
  "idempotency_key": "client-generated-uuid"
}
```

响应示例：

```json
{
  "session_id": "s_123",
  "ws_url": "/ws/voice/session?session_id=s_123",
  "language": "zh-CN",
  "stt_provider": "azure",
  "tts_provider": "azure",
  "recording_enabled": true,
  "expires_at": "2026-08-19T13:00:00+08:00"
}
```

## WebSocket 连接

路径：`/ws/voice/session`

推荐参数：

- `session_id`：必填，服务端创建的会话 ID。
- `token`：推荐，短期访问令牌。
- `client_seq_start`：可选，重连后客户端下一条音频序号。

示例：

```text
/ws/voice/session?session_id=s_123&token=<short_lived_token>
```

## 鉴权建议

- REST 通过登录态、服务端签名或招聘系统 token 鉴权。
- WebSocket 使用短期 token，绑定 `session_id`、候选人和过期时间。
- token 不应写入日志。
- 音频对象存储访问使用后端签名 URL，不暴露永久凭证。

## 错误码

| code | 含义 | 建议处理 |
|---|---|---|
| `AUTH_INVALID` | 鉴权失败 | 重新登录或刷新 token |
| `SESSION_NOT_FOUND` | 会话不存在 | 重新创建 session |
| `AUDIO_FORMAT_UNSUPPORTED` | 音频格式不支持 | 切换 PCM16 或服务端转码 |
| `STT_PROVIDER_ERROR` | STT provider 异常 | 降级文本输入或切换 provider |
| `TTS_PROVIDER_ERROR` | TTS provider 异常 | 降级文本展示 |
| `INTERRUPT_FAILED` | 打断取消失败 | 前端仍应停止播放 |
| `RATE_LIMITED` | 请求过载或限流 | 退避重试 |
| `INTERNAL_ERROR` | 未知错误 | 记录 trace 并提示稍后重试 |

## 幂等性与重连

- `POST /api/interview-sessions` 支持 `idempotency_key`，同一 key 在短时间内返回同一 session。
- `audio.chunk` 必须带 `seq`，服务端按 `session_id + seq` 去重。
- WebSocket 重连后客户端带上最近确认的 `seq`。
- 服务端对重复 `control.interrupt` 做幂等处理，同一 `turn_id` 多次取消只记录一次最终状态。

## 音频格式

推荐生产格式：

- codec：`pcm_s16le`
- sample_rate：`16000`
- channels：`1`
- chunk duration：`20-100ms`

浏览器可行替代：

- `audio/webm;codecs=opus`
- 后端需要转码为 provider 要求格式。
- 使用替代格式会增加 100-300ms 处理延迟。

## 环境变量示例

以下仅为配置名示例，不包含真实密钥。

```bash
APP_ENV=development
VOICE_SESSION_TOKEN_SECRET=replace_with_local_secret
DEFAULT_STT_PROVIDER=mock
DEFAULT_TTS_PROVIDER=mock

AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_STT_LANGUAGE=zh-CN
AZURE_TTS_VOICE=zh-CN-XiaoxiaoNeural

OPENAI_API_KEY=
TENCENT_ASR_SECRET_ID=
TENCENT_ASR_SECRET_KEY=
ALIYUN_NLS_ACCESS_KEY_ID=
ALIYUN_NLS_ACCESS_KEY_SECRET=

DATABASE_URL=postgresql://user:password@localhost:5432/interview_voice
AUDIO_BUCKET_NAME=
```


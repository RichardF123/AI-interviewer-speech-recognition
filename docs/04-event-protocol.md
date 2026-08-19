# WebSocket 事件协议

所有事件都包含 `type`、`session_id`、`timestamp_ms`。服务端应为持久化事件补充 `trace_id`。

## `audio.chunk`

- 方向：client -> server
- 触发时机：前端采集到音频片段时。
- 是否持久化：保存索引和指标；原始音频是否保存取决于授权。

字段：

- `seq`：客户端递增序号。
- `format`：音频格式。
- `audio_base64`：音频数据。

```json
{
  "type": "audio.chunk",
  "session_id": "s_123",
  "timestamp_ms": 1200,
  "seq": 42,
  "format": {
    "codec": "pcm_s16le",
    "sample_rate": 16000,
    "channels": 1
  },
  "audio_base64": "..."
}
```

## `control.interrupt`

- 方向：client -> server
- 触发时机：候选人开口打断或用户点击停止。
- 是否持久化：是。

```json
{
  "type": "control.interrupt",
  "session_id": "s_123",
  "timestamp_ms": 5800,
  "turn_id": "t_009",
  "reason": "user_speech_detected"
}
```

## `stt.partial`

- 方向：server -> client
- 触发时机：STT provider 输出临时识别结果。
- 是否持久化：建议持久化，用于调试；不进入 LLM。

```json
{
  "type": "stt.partial",
  "session_id": "s_123",
  "timestamp_ms": 2600,
  "utterance_id": "u_001",
  "text": "我之前主要负责",
  "start_ms": 1200,
  "end_ms": 2600,
  "confidence": 0.86
}
```

## `stt.final`

- 方向：server -> client
- 触发时机：STT provider 输出稳定识别结果或 TurnDetector 判定 utterance 完成。
- 是否持久化：是，进入 LLM。

```json
{
  "type": "stt.final",
  "session_id": "s_123",
  "timestamp_ms": 5300,
  "utterance_id": "u_001",
  "text": "我之前主要负责推荐系统的召回和排序模块。",
  "normalized_text": "我之前主要负责推荐系统的召回和排序模块。",
  "start_ms": 1200,
  "end_ms": 5200,
  "confidence": 0.91
}
```

## `assistant.text`

- 方向：server -> client
- 触发时机：LLM 生成可展示、可朗读回复。
- 是否持久化：是。

```json
{
  "type": "assistant.text",
  "session_id": "s_123",
  "timestamp_ms": 5900,
  "turn_id": "t_009",
  "text": "好的。那我想继续追问一下排序模块。你当时主要优化的是特征、模型结构，还是线上策略？"
}
```

## `tts.audio`

- 方向：server -> client
- 触发时机：TTS provider 生成音频 chunk。
- 是否持久化：保存元数据；音频是否保存取决于授权。

```json
{
  "type": "tts.audio",
  "session_id": "s_123",
  "timestamp_ms": 6500,
  "turn_id": "t_009",
  "seq": 1,
  "codec": "mp3",
  "sample_rate": 24000,
  "audio_base64": "..."
}
```

## `metrics.turn`

- 方向：server -> client
- 触发时机：turn 结束、打断或失败时。
- 是否持久化：是。

```json
{
  "type": "metrics.turn",
  "session_id": "s_123",
  "timestamp_ms": 7100,
  "turn_id": "t_009",
  "stt_first_partial_ms": 620,
  "stt_final_latency_ms": 820,
  "llm_first_token_ms": 430,
  "tts_first_audio_ms": 690,
  "end_to_end_first_audio_ms": 1940,
  "interrupt_latency_ms": null
}
```

## `error`

- 方向：server -> client
- 触发时机：鉴权、格式、provider、内部处理异常。
- 是否持久化：是。

```json
{
  "type": "error",
  "session_id": "s_123",
  "timestamp_ms": 7200,
  "code": "STT_PROVIDER_ERROR",
  "message": "语音识别服务暂时不可用，请稍后重试或切换文本输入。",
  "retryable": true,
  "trace_id": "trace_abc"
}
```


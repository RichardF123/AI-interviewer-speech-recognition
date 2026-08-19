# 可观测性与指标

## turn 级延迟指标

每个 turn 记录以下时间点：

- `audio_first_chunk_at`
- `audio_last_chunk_at`
- `stt_first_partial_at`
- `stt_final_at`
- `llm_request_at`
- `llm_first_token_at`
- `assistant_text_ready_at`
- `tts_request_at`
- `tts_first_audio_at`
- `tts_last_audio_at`
- `playback_started_at`
- `interrupt_received_at`
- `interrupt_ack_at`

## STT 指标

- 首字延迟：`stt_first_partial_at - audio_first_chunk_at`
- final 延迟：`stt_final_at - audio_last_chunk_at`
- partial 回滚次数。
- final confidence。
- provider 错误率。
- 离线复核 CER/WER。

## LLM 指标

- 首 token 延迟。
- 完整回复生成耗时。
- 输入 token、输出 token。
- 被打断 turn 的生成取消率。
- 安全边界触发次数。

## TTS 指标

- 首包延迟：`tts_first_audio_at - tts_request_at`
- 完整合成耗时。
- 音频 chunk 数量和大小。
- TTS 取消成功率。
- SSML 生成失败降级次数。

## 端到端指标

- 候选人说完到面试官首包播放：`tts_first_audio_at - audio_last_chunk_at`
- 候选人说完到字幕 final：`stt_final_at - audio_last_chunk_at`
- 候选人说完到完整播放完成：`tts_last_audio_at - audio_last_chunk_at`

## 打断指标

- 前端停止播放延迟。
- 后端收到 `control.interrupt` 延迟。
- TTS 取消确认延迟。
- 打断后误播放 chunk 数。
- 打断成功率。

## 错误率与断连率

- WebSocket 建连失败率。
- WebSocket 中途断连率。
- 音频格式错误率。
- STT/TTS provider 错误率。
- 限流率。
- 降级触发率。

## 日志事件结构

```json
{
  "trace_id": "trace_abc",
  "session_id": "s_123",
  "turn_id": "t_009",
  "event_type": "stt.final",
  "timestamp_ms": 5300,
  "provider": "azure",
  "payload": {
    "utterance_id": "u_001",
    "text": "我之前主要负责推荐系统的召回和排序模块。",
    "confidence": 0.91
  }
}
```

## Dashboard 建议

- 实时会话数、在线候选人数。
- p50/p95/p99 端到端首包延迟。
- STT final 延迟和 confidence 分布。
- TTS 首包延迟。
- 打断成功率和误播放 chunk 数。
- provider 错误率和限流率。
- WebSocket 断连率。
- 按浏览器、地区、provider、岗位维度筛选。


# MVP 开发计划

建议 2-4 周完成内测版。第一版目标是稳定跑通语音输入、LLM 编排、语音输出、打断和日志，不追求复杂拟人化。

## 第 1 周：协议、骨架与 mock 联调

任务：

- 搭建 Next.js 前端语音页面。
- 搭建 FastAPI 后端和 `/ws/voice/session`。
- 实现 `voice-events` TypeScript 类型和 Pydantic schema。
- 实现 mock STT、mock TTS。
- 实现 `AudioCaptureClient`、`VoiceSocketClient`、`PlaybackController` 骨架。
- 实现 `SessionLogger` 结构化日志。

验收：

- 无云服务配置时，可用 mock provider 完成一次端到端会话。
- 前端能展示 partial/final/assistant 文本。
- 前端能播放 mock TTS 音频占位或识别音频事件。

## 第 2 周：真实 STT/TTS provider 接入

任务：

- 接入 Azure Speech SDK STT，占位配置通过环境变量读取。
- 接入 Azure Neural TTS + SSML。
- 实现 `TranscriptNormalizer` 基础规则。
- 实现 `SpeechStyleFormatter` 基础清洗和断句。
- 增加 provider 错误处理和降级提示。

验收：

- 配置真实云账号后，可以完成中文普通话实时识别。
- AI 面试官回复能转成自然语音播放。
- 代码仓库不包含真实密钥。

## 第 3 周：打断、指标和会话质量

任务：

- 实现前端 VAD 或音量阈值检测候选人开口。
- 实现 `control.interrupt` 幂等处理。
- 后端取消当前 TTS 任务。
- 记录 turn 级指标：STT、LLM、TTS、端到端、打断延迟。
- 增加 WebSocket 重连和音频 seq 去重。

验收：

- 候选人开口 200ms 内前端停止播放。
- 后端 500ms 内记录打断取消结果。
- dashboard 或日志可查看核心指标。

## 第 4 周：评估、合规和内测准备

任务：

- 保存授权后的音频片段到对象存储。
- 抽样音频用 faster-whisper 或 FunASR 做离线复核。
- 输出 CER/WER 报告。
- 补齐候选人授权、录音提示、删除策略。
- 完成测试脚本和内测 checklist。

验收：

- 有 20-50 条真实内测会话样本。
- 可查看转写准确率、延迟分布、错误率、断连率。
- 合规文案和数据保存策略通过评审。

## 前端任务清单

- 麦克风授权和权限失败提示。
- `AudioWorklet` 或 `MediaRecorder` 采集。
- WebSocket 连接、断线重连、心跳。
- 字幕展示 partial/final。
- TTS 音频队列播放。
- 打断按钮和自动打断。
- 降级到文本输入。

## 后端任务清单

- REST 创建 session。
- WebSocket 事件收发。
- STT/TTS provider base class。
- Azure/mock provider。
- LLM 编排接口。
- transcript normalizer。
- session logger。
- provider 错误、重试和降级。

## 测试策略

- 单元测试：事件 schema、文本清洗、SSML 生成、provider mock。
- 集成测试：WebSocket 端到端事件顺序。
- 延迟测试：记录 p50/p95/p99。
- 打断测试：播放中、合成中、LLM 生成中三种情况。
- 合规测试：无授权时不保存原始音频。

## 降级策略

- STT 异常：提示候选人改用文本输入。
- TTS 异常：继续显示面试官文本，不播放语音。
- WebSocket 断连：暂停录音，自动重连，失败后手动恢复。
- provider 限流：退避重试，必要时切换备用 provider。


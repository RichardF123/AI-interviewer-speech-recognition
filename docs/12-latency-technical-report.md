# AI 面试官语音链路阶段汇报与低延迟技术报告

更新时间：2026-08-19

## 1. 项目目标

本项目目标是做一个可本地运行、可演示的 AI 面试官语音 Demo：

1. 候选人语音输入转文字，让 AI 面试官理解候选人回答。
2. AI 面试官基于候选人回答生成追问。
3. 追问文本转语音播放，音色和语气尽量自然。
4. 关键验收目标：候选人说完后 2-3 秒内，LLM 能收到可用候选人文本并开始生成文字反馈，随后 TTS 播放。

## 2. 当前已完成工作

### 2.1 前端展示

已完成 `app/frontend`：

- React + Vite + TypeScript 前端。
- 输出区在上方，候选人输入区在下方。
- 支持开始面试、实时回答、结束回答、打断、重置。
- 使用 Web Audio API 获取麦克风 PCM 音频。
- 使用浏览器 SpeechRecognition 作为低延迟字幕源，后端默认切换为 MiMo ASR 段式转写。
- 增加低延迟麦克风活动反馈：检测到声音后 100-250ms 内显示输入状态。
- 增加 `发送给 LLM` 调试行，展示真实进入大模型的候选人 final 文本。
- 明确区分候选人转写和系统状态，系统状态不会再被当成候选人答复。

### 2.2 后端链路

已完成 `app/backend`：

- FastAPI REST + WebSocket 后端。
- `POST /api/interview-sessions` 创建会话。
- `WS /ws/voice/session` 承载语音事件。
- 接入 DeepSeek Chat Completions。
- 接入阿里云 NLS Token 创建。
- 接入阿里云 NLS TTS HTTP 调用。
- 增加阿里云实时 ASR SDK 桥接 `AliyunRealtimeTranscriber`，保留为可切换方案。
- 新增 MiMo ASR `mimo-v2.5-asr` 接入：前端上传 PCM，后端在用户结束回答时封装为 WAV/base64 后调用 MiMo。
- 增加 `llm.input` 事件，把进入 LLM 的 final 文本回传前端。
- 禁止 ASR 无文本时触发 LLM，避免系统状态污染候选人回答。

### 2.3 版本管理

已推送到 GitHub `main` 分支。关键提交包括：

- `Fix realtime answer startup flow`
- `Add Aliyun realtime ASR bridge`
- `Prefer Aliyun PCM voice capture`
- `Add voice capture feedback fallback`
- `Speed up voice transcript feedback`
- `Tighten interviewer follow-up prompt`
- `Separate voice status from candidate transcript`
- `Add low latency microphone activity feedback`
- `Show LLM input and tighten grounding`

本地 `.env` 保存 API Key，不进入 Git。

## 3. 当前技术栈

前端：

- React
- Vite
- TypeScript
- WebSocket
- Web Audio API
- SpeechRecognition / webkitSpeechRecognition
- lucide-react

后端：

- Python
- FastAPI
- Uvicorn
- Pydantic
- 阿里云 NLS Python SDK
- MiMo Speech Recognition API
- DeepSeek Chat Completions
- WebSocket

## 3.1 MiMo ASR 切换说明

2026-08-19 已按最新要求把默认 ASR provider 从 `aliyun` 切到 `mimo`。

- 官方文档：https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/audio/Speech-Recognition
- 模型：`mimo-v2.5-asr`
- 输入：`wav` / `mp3` 音频，base64 或 Data URL。
- 当前实现：浏览器采集 16kHz PCM，后端在 `audio.stop` 后封装为 WAV，再调用 MiMo `/v1/chat/completions`。
- 能力边界：MiMo 当前文档示例是“整段音频转写”，不是麦克风音频流式上传，因此无法提供真正 ASR partial；2-3 秒目标依赖短回答、及时停止录音和接口响应速度。

## 3.2 电话式实时语音目标重定义

2026-08-19 再次收敛产品目标：本项目核心不是“面试内容智能体”，而是一个可以装载到任意微调大模型上的电话式实时语音交互承载层。

新的交互目标：

- 用户只点击一次“开始面试”。
- 系统自动请求麦克风并进入持续聆听。
- 页面不再要求用户点击“实时回答”或手动结束回答。
- 候选人说话时立即显示实时/准实时转写。
- 稳定 final 文本才进入 LLM，partial 只做字幕展示。
- LLM 输出文字立即显示，TTS 自动读出。
- AI 说完后自动回到聆听状态。
- 系统状态、静音提示、转写状态不能进入候选人文本。

当前 MVP 实现：

- 前端已切为电话模式入口：开始面试后自动开麦。
- 前端使用浏览器 `SpeechRecognition` 做实时字幕和低延迟 final 触发。
- 后端新增通用 `speech.final` 事件别名，替代 demo 专用事件。
- LLM prompt 改为“实时语音交互承载型 AI 面试官”，不再绑定具体面试内容。
- MiMo ASR 保留为分段兜底，不伪装成真正流式 ASR。
- 阿里云 TTS 优先输出真实 mp3；超时时前端使用浏览器 `speechSynthesis` 兜底播报。

下一步真正接近豆包电话体验，需要替换为：

- 持续 10-20ms 音频帧上传。
- 真正流式 ASR，支持 partial、endpointing、VAD。
- 流式 LLM，首 token 立即回前端。
- 流式 TTS，按句或 token chunk 合成音频。
- 播放中持续监听，检测候选人插话后 300ms 内打断 TTS。

外部服务：

- LLM：DeepSeek，当前模型名 `deepseek-chat`
- STT：阿里云 NLS 实时语音识别
- TTS：阿里云 NLS TTS

## 4. 当前链路

```text
候选人说话
  -> 浏览器 getUserMedia
  -> Web Audio API 采样
  -> 前端本地音量/VAD 反馈
  -> PCM 16k 单声道音频 WebSocket 上传
  -> 后端 AliyunRealtimeTranscriber
  -> 阿里云 NLS 返回 stt.partial / stt.final
  -> 后端发送 llm.input
  -> DeepSeek 生成追问
  -> 前端展示 assistant.text
  -> 阿里云 TTS / mock TTS 播放
```

并行低延迟路径：

```text
浏览器 SpeechRecognition 可用时
  -> 浏览器本地 interim/final 字幕
  -> final 直接提交给后端
  -> DeepSeek
```

## 5. 当前问题与根因判断

### 问题 1：语音识别仍然慢

现象：

- 页面能快速检测到麦克风有声音。
- 但候选人真实文字没有稳定出现。
- LLM 有时收不到用户真实回答。

判断：

- 前端麦克风采集已启动，音频已能发到后端。
- 真正瓶颈在 ASR 产出文字：阿里云实时 ASR 没有稳定返回 `stt.partial` / `stt.final`。
- 浏览器内置 SpeechRecognition 在当前 in-app browser 环境可能不可用或不稳定。

### 问题 2：LLM 输出不像基于用户输入

现象：

- 追问看起来泛泛而谈，或不像基于用户原话。

判断：

- DeepSeek Key 已验证有效。
- 已加入 `发送给 LLM` 展示行，接下来要看 LLM 实际收到的文本。
- 如果 `发送给 LLM` 不是用户真实回答，则问题是 ASR。
- 如果 `发送给 LLM` 正确但追问仍不相关，则继续优化 prompt 和 conversation state。

### 问题 3：TTS 仍不稳定

现象：

- 阿里云 TTS 可能 provider fallback。

判断：

- 需要继续确认阿里云 NLS TTS 服务开通、AppKey 所属项目、区域和音色权限。
- 当前系统可 fallback，不阻塞文字反馈。

## 6. 外部调研结论

公开资料对实时 voice agent 的共识是：不能把 STT、LLM、TTS 串行等待，必须让每个阶段尽早开始。

关键参考：

- 2026 年企业实时语音 Agent 论文指出，voice agent 需要 streaming STT，partial transcript 在用户说话时就要产生，用于降低延迟：https://arxiv.org/html/2603.05413v1
- 阿里云实时语音识别文档说明实时识别通过 WebSocket 转写音频流，适用于实时字幕、语音聊天、智能助手：https://www.alibabacloud.com/help/en/model-studio/real-time-speech-recognition-user-guide
- 阿里云智能语音交互 WebSocket 文档要求命令和音频流按协议发送，音频数据走二进制帧：https://www.alibabacloud.com/help/en/isi/developer-reference/websocket
- 实时语音 Agent 架构资料强调要区分 partial transcript、final transcript 和 endpointing latency：https://github.com/ombharatiya/ai-system-design-guide/blob/main/18-voice-and-audio-agents/01-realtime-voice-agents.md
- Voice AI 基础设施文章总结，Streaming ASR、LLM token streaming、Streaming TTS 应该并行，而不是离散串行：https://introl.com/blog/voice-ai-infrastructure-real-time-speech-agents-asr-tts-guide-2025
- Deepgram 低延迟 voice AI 资料强调，partial ASR 可以喂给 LLM，TTS 可在响应完成前开始播放：https://deepgram.com/learn/low-latency-voice-ai
- VAD/turn-taking 是级联 STT + LLM + TTS 架构里判断用户何时说完的关键：https://gradium.ai/content/turn-taking-voice-agents-vad

## 7. 2-3 秒目标架构

目标 SLA：

| 阶段 | 目标 |
| --- | --- |
| 麦克风活动反馈 | < 250ms |
| 首个 ASR partial | < 800ms |
| 端点检测/用户说完判断 | 静音 600-900ms |
| final 文本进入 LLM | 用户停止说话后 < 1200ms |
| LLM 首 token | < 800ms |
| 前端显示首段回答 | 用户停止说话后 2-3s 内 |
| TTS 首包 | LLM 首句后 < 1000ms |

推荐架构：

```text
Frontend
  - AudioWorklet / Web Audio PCM
  - 本地 VAD
  - 浏览器 SpeechRecognition 仅作为可选字幕源
  - WebSocket 上报 audio.chunk / vad.end / transcript.final

Backend Voice Gateway
  - 单会话状态机
  - ASR 长连接常驻
  - partial 聚合
  - endpointing 逻辑
  - final 去重与质量判断

ASR Provider
  - 阿里云 NLS 实时识别
  - 必须稳定返回 partial/final
  - 不可用时明确失败，不触发 LLM

LLM Orchestrator
  - 收到 final 或高置信 partial 后启动
  - 使用 streaming 输出
  - 前端立即显示首 token

TTS Provider
  - 句子级流式合成
  - 前端边收边播
```

## 8. 下一阶段 P0 改造

P0-1：确认阿里云 ASR 权限和协议

- 检查 AppKey 对应项目是否开通实时语音识别。
- 确认使用的服务是智能语音交互 NLS 还是 Model Studio Fun-ASR。
- 如果是 NLS SDK，继续使用 `NlsSpeechTranscriber`。
- 如果是 Fun-ASR WebSocket，则改用 DashScope/Model Studio 协议。
- 明确音频格式：PCM 16k、16bit、mono。

P0-2：后端端点检测

- 前端发送 `vad.speech_start`、`vad.speech_end`。
- 后端不再依赖用户点击结束。
- 静音 600-900ms 自动提交候选人 final。

P0-3：LLM 流式输出

- DeepSeek 改为 `stream: true`。
- 后端向前端发送 `assistant.delta`。
- 前端首 token 立即展示。

P0-4：TTS 流式/句子级合成

- 先按句切分 LLM 输出。
- 第一短句生成后立即送 TTS。
- 前端收到音频立即播放。

P0-5：端到端指标

必须记录：

- `mic_start_at`
- `first_audio_chunk_at`
- `first_asr_partial_at`
- `vad_end_at`
- `final_to_llm_at`
- `llm_first_token_at`
- `tts_first_audio_at`
- `audio_play_start_at`

## 9. 三 Agent 协作任务

Agent1：外部调研

- 调研实时 ASR / LLM / TTS 低延迟架构。
- 输出 P0/P1/P2 解决方案。
- 重点确认阿里云 NLS/Fun-ASR 的正确接入方式和低延迟参数。

Agent2：架构与提示词工程

- 基于当前仓库设计 2-3 秒链路。
- 输出给 Agent3 的文件级落地提示词。
- 明确不能再做的假兜底：状态不能当候选人文本、ASR 无文本不能触发 LLM。

Agent3：执行落地

- 实现低延迟链路指标。
- 实现 `assistant.delta`。
- 实现 VAD 自动结束。
- 保证构建通过。
- 输出修改文件和验证结果。

## 10. 产品经理验收标准

必须通过以下手工验收：

1. 点击实时回答后，250ms 内看到麦克风活动反馈。
2. 用户说一句完整回答后，不点按钮也能在静音后自动结束。
3. 页面显示 `发送给 LLM` 的文本必须是候选人真实回答。
4. `发送给 LLM` 为空或错误时，不允许 AI 面试官编造追问。
5. LLM 首段文字在用户停止说话后 2-3 秒内出现。
6. TTS 至少能播放首句，阿里云不可用时要明确显示 fallback 原因。

## 11. 当前结论

当前 Demo 已经从“静态 mock 页面”推进到“前端真实采音、后端真实 LLM、阿里云 ASR/TTS 接入尝试、链路可诊断”的阶段。

但要达到 2026 年可接受的 voice agent 体验，下一步必须把核心链路从“等待 ASR final 的串行流程”升级为：

```text
VAD + streaming ASR partial + streaming LLM + streaming / sentence-level TTS
```

当前最大风险不是前端 UI，而是阿里云 ASR 是否真的按当前 AppKey/服务类型稳定返回 partial/final。这个需要优先确认，否则任何 LLM 和 TTS 优化都会基于错误或空文本。

## 12. 三 Agent 执行结果

### Agent1：外部调研结果

Agent1 的结论是：2-3 秒目标可达，但前提是全链路流式，而不是串行等待完整结果。

关键建议：

- 浏览器 20-100ms 小帧上传。
- 使用 AudioWorklet 优先于 MediaRecorder。
- ASR 必须返回 interim/partial。
- 端点检测建议初始 300-500ms，面试长答可动态调高。
- LLM 关注 TTFT，不等完整回答。
- TTS 使用 WebSocket/streaming，收到首包即播。
- 记录 P50/P90/P95/P99，特别是 ASR endpointing、LLM TTFT、TTS TTFA。

### Agent2：架构设计结果

Agent2 判断当前最大瓶颈是：

- 前端职责混杂，浏览器识别与阿里云 ASR 并行但没有清晰 committed transcript。
- 音频使用 JSON + base64，开销偏高。
- LLM 非流式，当前 `stream: false`。
- TTS 是 REST 完整 MP3，不能稳定低首包。
- 仍要删除所有可能进入 LLM 的假候选人文本。

Agent2 给出的下一阶段架构：

```text
Browser AudioWorklet
  -> binary PCM WebSocket
  -> Backend TurnManager
  -> Aliyun partial/final
  -> VAD 600-900ms commit
  -> LLM streaming
  -> assistant.text.delta
  -> streaming TTS
  -> tts.audio.delta
```

### Agent3：已落地结果

Agent3 已在当前工作区落地：

- 前端新增本轮链路时间线：
  - `mic_start`
  - `first_audio_chunk`
  - `first_asr_partial`
  - `final_to_llm`
  - `llm_first_text`
  - `tts_first_audio`
- 前端展示 `发送给 LLM`，用于确认模型是否基于真实候选人文本。
- 后端增加候选人文本保护：空文本、系统状态文本、重复 final 不触发 LLM。
- ASR 无文本时只返回错误，不再假装候选人回答。

已验证：

```text
npm run build
python -m compileall app
git diff --check
```

### 产品经理监督结论

当前版本已经具备“定位瓶颈”的能力：

- 如果 `first_audio_chunk` 很快，但 `first_asr_partial` 不出现，瓶颈是 ASR 服务或协议。
- 如果 `final_to_llm` 出现，但 `llm_first_text` 慢，瓶颈是 LLM。
- 如果 `llm_first_text` 出现，但 `tts_first_audio` 慢，瓶颈是 TTS。

下一步不应继续做 UI 状态补丁，而应进入 P0 架构改造：

1. WebSocket binary PCM，替代 base64 JSON 主路径。
2. 后端 TurnManager，统一管理 partial、final、commit、去重。
3. partial promotion：用户停顿时，如果没有 final 但已有真实 partial，可提交 latest partial。
4. DeepSeek 改 streaming，前端处理 `assistant.text.delta`。
5. 阿里云 TTS 改 streaming，前端处理 `tts.audio.delta`。

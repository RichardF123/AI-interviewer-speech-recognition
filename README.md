# AI Interviewer Speech Recognition

电话式 AI 面试语音链路 Demo。目标是验证一条可装载到任意大模型上的实时语音承载层：

```text
候选人说话 -> 实时/准实时转写 -> final 文本进入 LLM -> AI 输出文字 -> 自动语音播报
```

当前版本已经不是纯 mock。项目已接入：

- LLM：DeepSeek Chat Completions
- 实时 ASR 主链路：阿里云 NLS 实时语音识别
- 分段 ASR 备份：MiMo `mimo-v2.5-asr`
- TTS：阿里云 NLS TTS，前端浏览器 `speechSynthesis` 兜底
- 前端实时字幕优先使用浏览器 `SpeechRecognition`

## 当前能力

- 点击一次“开始面试”后进入电话式会话。
- 自动请求麦克风权限，不再要求手动点击“实时回答”。
- 候选人说话时，前端优先用浏览器实时字幕显示 partial。
- 稳定 final 文本通过 WebSocket 发送给后端。
- 后端把 final 文本送入 DeepSeek，partial 不进入 LLM。
- AI 面试官文字回复立即展示。
- 前端优先自动朗读 AI 回复，阿里云 TTS 可用时也会返回真实 mp3。
- 多轮输入采用“最新输入优先”，避免上一轮 LLM/TTS 卡住下一轮。
- 系统状态、麦克风状态、转写状态不会被当作候选人回答。

## 技术栈

前端：

- React
- Vite
- TypeScript
- Web Audio API
- SpeechRecognition / webkitSpeechRecognition
- WebSocket
- Browser speechSynthesis
- lucide-react

后端：

- Python
- FastAPI
- Uvicorn
- Pydantic
- WebSocket
- DeepSeek Chat Completions
- 阿里云 NLS Python SDK
- MiMo Speech Recognition API

## 当前链路

```text
Browser
  -> getUserMedia 获取麦克风
  -> Web Audio API 采集 16k PCM
  -> SpeechRecognition 显示实时字幕
  -> speech.final 发送稳定文本

FastAPI WebSocket
  -> stt.final
  -> llm.input
  -> DeepSeek
  -> assistant.text
  -> Aliyun TTS / Browser TTS
```

后端同时会尝试启动阿里云实时 ASR：

```text
audio.chunk -> AliyunRealtimeTranscriber -> stt.partial / stt.final
```

如果阿里云实时 ASR 因网络或权限超时，页面仍可通过浏览器 `SpeechRecognition` 完成实时字幕和 final 提交。

## 本地运行

后端：

```powershell
cd app/backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

前端：

```powershell
cd app/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5185
```

访问：

```text
http://127.0.0.1:5185/
```

健康检查：

```text
http://127.0.0.1:8011/health
http://127.0.0.1:8011/api/provider-status
```

## 环境变量

后端读取 `app/backend/.env`。真实密钥不要提交到 Git。

```env
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

ALIYUN_NLS_APP_KEY=
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
ALIYUN_NLS_TOKEN=
ALIYUN_NLS_ENDPOINT=wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1
ALIYUN_TTS_ENDPOINT=https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts
ALIYUN_TTS_VOICE=zhixiaoxia

MIMO_API_KEY=
MIMO_BASE_URL=https://api.xiaomimimo.com/v1
MIMO_ASR_MODEL=mimo-v2.5-asr
MIMO_ASR_LANGUAGE=zh
```

## API 服务说明

DeepSeek：

- 用于 AI 面试官文本回复。
- 当前 prompt 定位为“实时语音交互承载型 AI 面试官”，不绑定具体面试内容。
- 后续可替换为微调后的 OpenAI-compatible 模型。

阿里云 NLS：

- 实时 ASR：目标是提供后端 `stt.partial` / `stt.final`。
- TTS：生成真实 mp3 语音。
- 若实时 ASR WebSocket 连接超时，需要检查阿里云项目是否开通实时语音识别、AppKey 所属项目、AccessKey 权限和本机网络。

MiMo：

- 当前 `mimo-v2.5-asr` 是音频文件/base64 转写，不是真正流式 ASR。
- 适合作为录音片段兜底，不适合作为豆包电话式实时字幕主链路。

## 已知限制

- Codex 内置浏览器可能不支持 `SpeechRecognition`，推荐用 Chrome 或 Edge 访问本地页面。
- MiMo 不支持麦克风音频流式 partial。
- 阿里云实时 ASR 如果网络或权限不通，会返回启动超时；此时不会伪造候选人文本。
- 当前 LLM 仍是非 streaming 请求，文字首响已经可用，但还不是 token 级流式。
- 当前 TTS 优先保证“听得到”，后续应升级为真正流式 TTS。

## 下一步技术路径

要接近豆包电话体验，需要继续升级为全流式链路：

```text
AudioWorklet 10-20ms PCM
  -> 流式 ASR partial/final
  -> 流式 LLM token
  -> 句子级/流式 TTS
  -> 播放中 VAD barge-in 打断
```

优先级：

1. 确认阿里云实时 ASR WebSocket 权限和网络，稳定返回 partial/final。
2. 将 DeepSeek 调用升级为 streaming，前端立即显示 delta。
3. 将 TTS 改成流式合成和播放队列。
4. 增加本地 VAD 和回声消除，AI 播放时也能检测用户插话。
5. 抽象 provider，让项目可以直接切换到微调好的大模型或端到端实时语音模型。

## 文档

- `docs/12-latency-technical-report.md`：阶段汇报、延迟分析和实时语音方案。
- `app/backend/README.md`：后端接口和 provider 说明。
- `app/frontend/README.md`：前端电话式交互说明。

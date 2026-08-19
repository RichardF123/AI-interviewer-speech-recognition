# AI 面试官语音识别 Demo

本项目是 AI 面试官语音功能的第一版 Demo 方案与开发骨架，目标是打通“候选人说话 -> 语音识别转文字 -> AI 面试官理解并生成回复 -> 回复转语音播放”的基础链路。

当前仓库重点交付两部分：

- `app/frontend`：可运行的 Vite + React + TypeScript 前端展示控制台。
- `app/backend`：可运行的 FastAPI mock 后端，提供 REST session 创建和 WebSocket 语音事件链路。
- `docs/`：产品、架构、接口、事件协议、Prompt、TTS 风格、MVP 计划、风险合规和汇报材料。
- `scaffold/`：更细的前后端开发骨架，包含 provider 抽象、播放控制和模块边界。

当前版本不包含真实外部 API 接入，不包含真实 API Key、Secret 或 Token。默认链路使用 mock provider，用于演示交互流程、评审技术方案和继续开发。

## 目录结构

```text
.
├── docs/
│   ├── 00-overview.md
│   ├── 01-prd.md
│   ├── 02-architecture.md
│   ├── 03-api-contract.md
│   ├── 04-event-protocol.md
│   ├── 05-prompt-templates.md
│   ├── 06-tts-style-templates.md
│   ├── 07-mvp-development-plan.md
│   ├── 08-risk-and-compliance.md
│   ├── 09-observability-and-metrics.md
│   ├── 10-demo-report.md
│   └── 11-deploy-and-api-keys.md
├── app/
│   ├── frontend/
│   │   ├── package.json
│   │   └── src/
│   └── backend/
│       ├── requirements.txt
│       └── app/
└── scaffold/
    ├── frontend/
    │   └── src/
    │       ├── audio/
    │       ├── types/
    │       └── ws/
    └── backend/
        └── app/
            ├── api/
            ├── core/
            ├── schemas/
            ├── services/
            └── ws/
```

## 当前 Demo 能力

当前 mock 链路用于展示端到端事件流：

1. 前端采集麦克风音频，按 chunk 通过 WebSocket 发送。
2. 后端 `mock STT` 生成 `stt.partial` 和 `stt.final`。
3. 只有 `stt.final` 会进入面试编排逻辑。
4. `InterviewOrchestrator` 生成面试官文本回复。
5. 后端 `mock TTS` 生成 `tts.audio` 占位事件。
6. 前端接收文本、语音事件，并支持 `control.interrupt` 打断控制。

这个版本适合用于产品演示、研发评审和接口联调，不适合作为生产系统直接上线。

## 启动后端

进入可运行后端目录：

```bash
cd app/backend
```

创建虚拟环境并安装依赖：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

启动 FastAPI：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

默认服务地址：

```text
http://127.0.0.1:8000
```

健康检查：

```text
GET /health
```

核心接口：

- `POST /api/interview-sessions`
- `WS /ws/voice/session`

## 启动前端

进入可运行前端目录：

```powershell
cd app/frontend
npm install
npm run dev
```

默认访问：

```text
http://127.0.0.1:5173
```

前端会优先连接 `http://127.0.0.1:8000` 的后端 mock 服务；如果后端未启动，会自动降级到本地模拟模式。

## 上线

当前仓库已添加 GitHub Pages 自动部署 workflow：

```text
.github/workflows/deploy-frontend.yml
```

推送到 `main` 后会自动构建 `app/frontend` 并发布前端页面。首次使用时，请到 GitHub 仓库 `Settings -> Pages`，把发布来源设置为 `GitHub Actions`。

预计访问地址：

```text
https://richardf123.github.io/AI-interviewer-speech-recognition/
```

更完整的上线和 API 获取说明见：

- `docs/11-deploy-and-api-keys.md`

当前前端技术栈：

- React + Vite
- TypeScript
- Web Audio API 麦克风授权检查
- WebSocket
- lucide-react 图标

## 需要的 API 服务

当前 Demo 不依赖真实外部 API。进入真实 MVP 时，需要准备以下服务：

- STT：Azure Speech SDK，或腾讯云实时语音识别，或阿里云智能语音交互。
- TTS：Azure Neural TTS，或 OpenAI TTS。
- LLM：用于面试官理解、追问和评分的模型服务。
- 存储：PostgreSQL 保存会话、事件和指标；S3/OSS/COS 保存授权后的音频片段。
- 可观测性：OpenTelemetry、Prometheus/Grafana、ELK 或同类日志指标系统。

## Provider 接入位置

STT provider：

- 当前可运行 mock：`app/backend/app/mock_services.py`
- 抽象设计参考：`scaffold/backend/app/services/stt/base.py`
- Azure 占位参考：`scaffold/backend/app/services/stt/azure.py`

TTS provider：

- 当前可运行 mock：`app/backend/app/mock_services.py`
- 抽象设计参考：`scaffold/backend/app/services/tts/base.py`
- Azure 占位参考：`scaffold/backend/app/services/tts/azure.py`

配置入口：

- 可运行后端：`app/backend/app/config.py`
- 抽象骨架：`scaffold/backend/app/core/config.py`

建议环境变量：

```bash
APP_ENV=development
DEFAULT_STT_PROVIDER=mock
DEFAULT_TTS_PROVIDER=mock
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_TTS_VOICE=zh-CN-XiaoxiaoNeural
DATABASE_URL=
AUDIO_BUCKET_NAME=
```

不要把真实密钥提交到仓库。生产环境应通过密钥管理系统或部署平台环境变量注入。

## 使用注意事项

- `stt.partial` 只用于前端字幕展示，不进入 LLM。
- `stt.final` 或稳定后的 utterance 才能进入面试官编排逻辑。
- 候选人开口打断时，前端应立即停止当前播放队列，并向后端发送 `control.interrupt`。
- TTS 前必须做文本清洗、断句和风格包装，避免直接朗读 Markdown、代码块、复杂编号或过长句子。
- Edge TTS、ChatTTS、Bark 等方案只适合作为非商用研究或 demo 参考，不作为商业默认方案。
- 真实上线前必须补齐候选人授权、录音告知、数据删除、访问控制、审计和供应商数据处理评估。

## 推荐阅读

- `docs/02-architecture.md`：整体架构和时序。
- `docs/03-api-contract.md`：REST 和 WebSocket 契约。
- `docs/04-event-protocol.md`：事件协议。
- `docs/06-tts-style-templates.md`：面试官语音风格。
- `docs/10-demo-report.md`：汇报材料。

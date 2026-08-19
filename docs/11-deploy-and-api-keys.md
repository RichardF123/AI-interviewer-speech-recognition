# 上线与 API 获取说明

## 当前上线策略

第一版先上线前端展示页，使用 GitHub Pages 自动部署。

原因：

- GitHub 仓库可以直接托管 Vite 构建后的静态页面。
- 当前后端是 FastAPI mock 服务，GitHub Pages 不能运行 Python 后端。
- 前端已经支持后端不可用时自动降级到本地模拟模式，所以可以先上线给产品和研发评审。

上线入口：

- 代码推送到 `main` 后，`.github/workflows/deploy-frontend.yml` 会自动构建 `app/frontend`。
- GitHub Pages 发布目录来自 `app/frontend/dist`。
- 首次使用时，需要在 GitHub 仓库的 `Settings -> Pages` 中选择 `GitHub Actions` 作为发布来源。

预计访问地址：

```text
https://richardf123.github.io/AI-interviewer-speech-recognition/
```

## 后端上线策略

真实后端不能放在 GitHub Pages。后续可以选：

| 方案 | 适合阶段 | 说明 |
|---|---|---|
| Render / Railway / Fly.io | 快速 MVP | 部署 FastAPI 简单，适合早期验证 |
| Azure App Service | 使用 Azure Speech 时 | 语音服务和后端在同一云上更方便管理 |
| 腾讯云 / 阿里云轻量服务器或函数计算 | 中国大陆部署 | 网络和合规路径更清晰 |
| 自有 Kubernetes | 正式生产 | 适合多租户、高并发、可观测性完整场景 |

前端接真实后端时，在部署平台中设置：

```bash
VITE_API_BASE=https://your-backend.example.com
```

## 需要哪些 API

当前 Demo 不需要真实 API。进入 MVP 时建议准备：

1. STT API：候选人语音转文字。
2. TTS API：AI 面试官文本转语音。
3. LLM API：理解候选人回答，生成追问、总结和评分辅助。
4. 数据库：保存 session、turn、事件、指标。
5. 对象存储：保存候选人授权后的音频片段。

## OpenAI API 获取

用途：

- LLM 面试官理解与追问。
- 可选使用 OpenAI TTS 做文本转语音。

获取方式：

1. 登录 OpenAI Platform。
2. 进入 API keys 页面。
3. 创建新的 API key。
4. 把 key 放到后端环境变量，不要写进前端代码。

建议环境变量：

```bash
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_TTS_MODEL=
OPENAI_TTS_VOICE=
```

## Azure Speech API 获取

用途：

- STT：实时语音识别。
- TTS：自然语音合成，支持 SSML 控制语速、停顿、音高和风格。

获取方式：

1. 登录 Azure Portal。
2. 创建 Speech 或 Azure AI Speech 资源。
3. 部署完成后进入资源详情。
4. 在 `Keys and Endpoint` 中查看 key 和 region。
5. 后端配置 key 与 region，region 必须和资源所在区域一致。

建议环境变量：

```bash
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_TTS_VOICE=zh-CN-XiaoxiaoNeural
```

## 腾讯云语音 API 获取

用途：

- 国内实时 ASR。
- 国内实时 TTS。

获取方式：

1. 登录腾讯云控制台。
2. 开通实时语音识别或语音合成服务。
3. 进入 API 密钥管理页面。
4. 新建密钥，获得 `AppID`、`SecretID`、`SecretKey`。
5. 后端用这些字段生成签名并调用 WebSocket API。

建议环境变量：

```bash
TENCENT_APP_ID=
TENCENT_SECRET_ID=
TENCENT_SECRET_KEY=
TENCENT_ASR_ENGINE_MODEL_TYPE=
TENCENT_TTS_VOICE_TYPE=
```

## 阿里云智能语音 API 获取

用途：

- 国内或亚太区域实时语音识别。
- 语音合成。

获取方式：

1. 登录阿里云控制台。
2. 开通智能语音交互服务。
3. 建议创建 RAM 用户，不要直接使用主账号 AccessKey。
4. 给 RAM 用户授予调用智能语音交互所需权限。
5. 创建 AccessKey ID 和 AccessKey Secret。
6. 后端先换取临时 token，再用 token 调用 WebSocket 服务。

建议环境变量：

```bash
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
ALIYUN_NLS_APP_KEY=
ALIYUN_NLS_ENDPOINT=
```

## 密钥使用注意事项

- 所有 API key 只放后端环境变量。
- 不要把 key 写入前端 `.env`，也不要提交到 GitHub。
- 生产环境使用云平台 Secret Manager 或部署平台的环境变量。
- 候选人音频属于敏感数据，需要授权、告知、访问控制和删除策略。
- 开源 TTS 或非正式接口上线前必须做 license 审查。

## 推荐接入顺序

1. 保持当前 mock 前后端，先完成产品演示。
2. 接入真实 LLM，让追问变成真实生成。
3. 接入真实 TTS，让面试官声音自然。
4. 接入真实 STT，让候选人真实说话转文字。
5. 增加数据库、对象存储、日志指标和评估任务。

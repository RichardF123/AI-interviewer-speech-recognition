# 后端骨架

本目录是 FastAPI 后端骨架，展示 REST、WebSocket、STT/TTS provider、orchestrator 和日志模块边界。

## 建议依赖

```bash
pip install fastapi uvicorn pydantic pydantic-settings
```

真实云 provider 接入时再安装对应 SDK，例如 Azure Speech SDK。当前 `azure.py` 只是占位实现，不会连接外部服务。

## 启动方向

```bash
uvicorn app.main:app --reload
```

## 环境变量

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

不要把真实密钥提交到仓库。生产环境应通过密钥管理系统注入。


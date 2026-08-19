from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    default_stt_provider: str = "mock"
    default_tts_provider: str = "mock"
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_stt_language: str = "zh-CN"
    azure_tts_voice: str = "zh-CN-XiaoxiaoNeural"
    database_url: str | None = None
    audio_bucket_name: str | None = None


settings = Settings()


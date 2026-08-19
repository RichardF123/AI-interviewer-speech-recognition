from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Interviewer Voice Mock Backend"
    app_env: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000
    default_stt_provider: str = "mock"
    default_tts_provider: str = "mock"
    default_voice_profile: str = "professional_warm_female"
    mock_tts_chunk_delay_ms: int = 180

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()


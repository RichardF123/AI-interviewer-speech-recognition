from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Interviewer Voice Mock Backend"
    app_env: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000
    default_stt_provider: str = "mock"
    default_llm_provider: str = "mock"
    default_tts_provider: str = "mock"
    default_voice_profile: str = "professional_warm_female"
    mock_tts_chunk_delay_ms: int = 180
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""
    aliyun_nls_app_key: str = ""
    aliyun_nls_token: str = ""
    aliyun_tts_voice: str = "zhixiaoxia"
    aliyun_nls_endpoint: str = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

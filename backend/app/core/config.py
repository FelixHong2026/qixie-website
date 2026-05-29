from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "AI Chinese Learning Platform"
    app_version: str = "0.1.0"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_chinese"

    # JWT
    secret_key: str = "change-this-to-a-random-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # ZhipuAI (GLM-4-Flash)
    zhipuai_api_key: Optional[str] = None
    zhipuai_api_base: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipuai_model: str = "glm-4-flash"

    # PayPal
    paypal_client_id: Optional[str] = None
    paypal_client_secret: Optional[str] = None
    paypal_mode: str = "sandbox"
    paypal_webhook_id: Optional[str] = None
    app_base_url: str = "http://localhost:5173"

    # Azure TTS
    azure_tts_key: Optional[str] = None
    azure_tts_region: str = "eastasia"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

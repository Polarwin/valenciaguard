"""Application settings, loaded from environment / .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./valenciaguard.db"
    secret_key: str = "dev-secret-change-me"
    upload_dir: str = "uploads"

    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "kimi-k2"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    notify_email: str = ""  # admin notification recipient

    cjk_font_path: str = ""
    irav_rate: float = 0.0214
    cost_threshold: float = 200.0


settings = Settings()

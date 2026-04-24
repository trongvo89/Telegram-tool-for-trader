from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    stars_provider_token: str = ""
    database_url: str = "sqlite+aiosqlite:///./bot.db"
    twelvedata_api_key: str = ""

    premium_monthly_stars: int = 500
    premium_yearly_stars: int = 4000

    owner_tg_id: int | None = None

    health_host: str = "0.0.0.0"
    health_port: int = 8080

    log_level: str = "INFO"


settings = Settings()

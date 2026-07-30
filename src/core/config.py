from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trading System"
    redis_url: str
    finnhub_api: str
    db_url: str
    newsapi_key: str
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_paper: bool = True
    discord_webhook_url: str = ""
    api_key: str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trading System"
    redis_url: str
    finnhub_api: str
    newsapi_key: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

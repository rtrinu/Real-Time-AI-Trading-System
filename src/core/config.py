from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Trading System"
    redis_url: str = "redis://localhost:6379"


settings = Settings()

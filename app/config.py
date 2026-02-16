from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Telegram RPG MVP API"
    app_version: str = "0.2.0"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rpg"
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

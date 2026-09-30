import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database - supports both PostgreSQL and SQLite
    DB_TYPE: str = "sqlite"  # "postgres" or "sqlite"
    DATABASE_URL: str = "sqlite+aiosqlite:///./videocrawler.db"
    DATABASE_URL_SYNC: str = "sqlite:///./videocrawler.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-a-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Download
    DOWNLOAD_DIR: str = "./downloads"

    # App
    APP_NAME: str = "视频下载助手"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure download directory exists
os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)

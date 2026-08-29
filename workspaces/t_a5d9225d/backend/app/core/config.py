"""Core configuration for ChainForge."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "ChainForge"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database (SQLite for local-first)
    DATABASE_URL: str = "sqlite:///./chainforge.db"

    # Execution
    MAX_EXECUTION_STEPS: int = 500
    EXECUTION_TIMEOUT: int = 300  # seconds

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    # Templates
    TEMPLATES_DIR: str = "./templates"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

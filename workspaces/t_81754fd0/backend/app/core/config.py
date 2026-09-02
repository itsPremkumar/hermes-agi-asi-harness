"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "UIGenerator"
    version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]
    max_generation_tokens: int = 4096
    component_library_path: str = "shared/components"

    class Config:
        env_prefix = "UIGENERATOR_"


settings = Settings()

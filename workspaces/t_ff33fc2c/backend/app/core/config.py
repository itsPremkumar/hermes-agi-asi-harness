from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "TaskForge"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/taskforge"
    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    github_client_id: str = ""
    github_client_secret: str = ""
    gitlab_url: str = "https://gitlab.com"
    gitlab_client_id: str = ""
    gitlab_client_secret: str = ""

    class Config:
        env_prefix = "TASKFORGE_"


settings = Settings()

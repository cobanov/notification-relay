from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "notifications"
    postgres_host: str = "db"
    postgres_port: int = 5432
    
    api_key: str = "your-secret-api-key-change-this"
    allowed_origins: str = "*"

    # Dashboard session (password-only login using the API key)
    session_cookie_name: str = "nr_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7  # 7 days
    cookie_secure: bool = False
    
    debug: bool = False
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

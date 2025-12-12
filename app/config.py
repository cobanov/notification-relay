from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database settings
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "notifications"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # API settings
    api_key: str = "your-secret-api-key-change-this"
    allowed_origins: str = "*"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


settings = Settings()

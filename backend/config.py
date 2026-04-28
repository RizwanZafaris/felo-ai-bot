from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""

    DATABASE_URL: str = "postgresql+asyncpg://felo:felo@localhost/felo_coach"
    REDIS_URL: str = "redis://localhost:6379"

    DEFAULT_PROVIDER: str = "anthropic"
    DEFAULT_MODEL: str = "claude-sonnet-4-6"

    SESSION_TTL_MINUTES: int = 30
    MAX_SESSION_MESSAGES: int = 20

    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"


settings = Settings()

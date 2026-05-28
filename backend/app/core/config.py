from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    # MyAnimeList OAuth credentials
    MAL_CLIENT_ID: str
    MAL_CLIENT_SECRET: str
    ENCRYPTION_KEY: bytes

    # Application URLs
    FRONTEND_URL: str = 'http://localhost:3000'
    BACKEND_URL: str = 'http://localhost:8002'

    DEBUG: bool = False
    LOG_LEVEL: str = 'INFO'

    # Observability — optional, disabled when unset
    SENTRY_DSN: str | None = None

    model_config = SettingsConfigDict(env_file='.env.backend')


settings = Settings()

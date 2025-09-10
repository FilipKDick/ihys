from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str  # For server-side operations
    SUPABASE_ANON_KEY: str     # For client-side operations
    SUPABASE_PASS: str | None = None  # Optional password field
    
    # MyAnimeList OAuth credentials
    MAL_CLIENT_ID: str
    MAL_CLIENT_SECRET: str
    ENCRYPTION_KEY: bytes

    # Application URLs
    FRONTEND_URL: str = 'http://localhost:3000'
    BACKEND_URL: str = 'http://localhost:8002'

    # Debug mode
    DEBUG: bool = False

    model_config = SettingsConfigDict(env_file='.env.backend')


settings = Settings()

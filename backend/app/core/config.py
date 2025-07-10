from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    MAL_CLIENT_ID: str
    MAL_CLIENT_SECRET: str
    ENCRYPTION_KEY: bytes

    # This points to our frontend, used for redirecting after login
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env.backend")

settings = Settings()
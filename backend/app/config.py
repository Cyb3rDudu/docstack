from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DocStack API"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # External Services
    OPENSEARCH_URL: str
    HAYHOOKS_URL: str

    # Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    SESSION_EXPIRE_HOURS: int = 24

    # Security
    BCRYPT_ROUNDS: int = 12

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://10.36.0.111:3000",
        "http://docstack.local"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

import os
from dataclasses import dataclass


@dataclass
class BaseConfig:
    APP_NAME: str = os.getenv("APP_NAME", "ipfs-gateway")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    TESTING: bool = False

    # Logging
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/ipfs_gateway")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Admin API key
    ADMIN_API_KEY: str | None = os.getenv("ADMIN_API_KEY")

    # Filebase IPFS (S3)
    FILEBASE_IPFS_API_KEY: str | None = os.getenv("FILEBASE_IPFS_API_KEY")
    FILEBASE_S3_ENDPOINT: str = os.getenv("FILEBASE_S3_ENDPOINT", "https://s3.filebase.com")
    FILEBASE_BUCKET: str = os.getenv("FILEBASE_BUCKET", "ipfs-gateway")


class DevConfig(BaseConfig):
    DEBUG = True


class StagingConfig(BaseConfig):
    DEBUG = False


class ProdConfig(BaseConfig):
    DEBUG = False


def get_config(env: str | None = None):
    env = env or os.getenv("APP_ENV", "development")
    if env == "development":
        return DevConfig()
    if env == "staging":
        return StagingConfig()
    if env == "production":
        return ProdConfig()
    return DevConfig()

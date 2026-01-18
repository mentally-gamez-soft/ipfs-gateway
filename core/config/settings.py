from google.cloud import secretmanager
import os
from dataclasses import dataclass, field


def get_prod_db_url():
    """Get production database URL or fall back to default."""
    return os.getenv("DATABASE_URL_PROD", "postgresql+psycopg2://user:pass@localhost:5432/ipfs_gateway")


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
    S3_ACCESS_KEY: str | None = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_ACCESS_KEY: str | None = os.getenv("S3_SECRET_ACCESS_KEY")
    ADMIN_API_KEY: str | None = os.getenv("ADMIN_API_KEY")


class DevConfig(BaseConfig):
    DEBUG = True


@dataclass
class StagingConfig(BaseConfig):
    def load_secret(project_id: str, name: str) -> str:
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}/secrets/{name}/versions/latest"
        resp = client.access_secret_version(name=parent)
        return resp.payload.data.decode("utf-8")

    DEBUG: bool = False    

    PROJECT_ID = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    for key in [
        "FILEBASE_IPFS_API_KEY",
        "FILEBASE_BUCKET",
        "S3_ACCESS_KEY",
        "S3_SECRET_ACCESS_KEY",
        "ADMIN_API_KEY",
        "DATABASE_URL_PROD",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND",
    ]:
        if PROJECT_ID:
            os.environ[key] = os.environ.get(key) or load_secret(PROJECT_ID, key)
    # Use production database for staging environment
    DATABASE_URL: str = os.getenv("DATABASE_URL_PROD", get_prod_db_url())


@dataclass
class ProdConfig(BaseConfig):
    DEBUG: bool = False
    # Use production database for production environment
    DATABASE_URL: str = field(default_factory=get_prod_db_url)


def get_config(env: str | None = None):
    env = env or os.getenv("APP_ENV", "development")
    print(f"Loading configuration for environment: {env}")
    if env == "development":
        return DevConfig()
    elif env == "staging":
        return StagingConfig()
    elif env == "production":
        return ProdConfig()
    return DevConfig()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # General
    environment: str = "production"
    secret_key: str = "change-me"
    allowed_hosts: str = "localhost"
    api_v1_prefix: str = "/api/v1"

    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "sentinel_rag"
    postgres_user: str = "sentinel"
    postgres_password: str = ""

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = ""
    minio_root_password: str = ""
    minio_use_ssl: bool = False

    # Ollama
    ollama_host: str = "http://ollama:11434"

    # LLM Providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    default_llm_provider: str = "ollama"
    default_embedding_provider: str = "ollama"

    # OIDC
    oidc_issuer_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""

    # Proxy
    http_proxy: str = ""
    https_proxy: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    @property
    def celery_broker_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/1"

    @property
    def celery_result_backend(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/2"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()

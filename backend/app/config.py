from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, overridable via environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CINEREC_", extra="ignore")

    database_url: str = "postgresql+psycopg://cinerec:cinerec@localhost:5432/cinerec"

    # Embedding backend: "sentence-transformers" (semantic, default) or "hash" (fast, offline).
    embedder: str = "sentence-transformers"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Collaborative filtering (implicit ALS) hyper-parameters.
    als_factors: int = 64
    als_iterations: int = 20
    als_regularization: float = 0.05

    # Recommendation cache. If a Redis URL is set and reachable it is used; otherwise the
    # service transparently falls back to an in-process TTL cache.
    redis_url: str | None = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    # Background ALS retraining: a worker thread retrains off the request path when new
    # ratings arrive (signal-driven) so requests never block on training.
    enable_background_retrain: bool = True
    retrain_interval_seconds: int = 60

    # Optional TMDB enrichment (not required for the MovieLens demo).
    tmdb_api_key: str | None = None

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

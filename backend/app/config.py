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
    # Where the fitted ALS model is persisted so it survives restarts and warm-loads on
    # startup (empty string disables persistence).
    als_model_path: str = "data/als_model.npz"

    # Optional TMDB enrichment (not required for the MovieLens demo).
    tmdb_api_key: str | None = None

    # Allowed CORS origins as a comma-separated list (so it is easy to set via a single env var
    # on hosting platforms). Use "*" to allow any origin. Bare hostnames are assumed https.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Observability / logging.
    log_level: str = "INFO"
    log_json: bool = True  # structured JSON logs (disable for human-readable dev logs)
    metrics_enabled: bool = True  # expose Prometheus metrics at /metrics
    tracing_enabled: bool = False  # OpenTelemetry tracing (opt-in; needs an OTLP endpoint)
    otlp_endpoint: str | None = None  # e.g. http://localhost:4317

    # Rate limiting (slowapi). Applied per client IP; empty string disables.
    rate_limit: str = "120/minute"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse ``cors_origins`` into a normalised list of origins.

        Accepts a comma-separated string; ``"*"`` means "allow any origin". Entries without a
        scheme are assumed to be ``https`` (convenient when a hosting platform injects a bare
        hostname). Trailing slashes are stripped so origins match the browser ``Origin`` header.
        """
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        origins: list[str] = []
        for part in raw.split(","):
            origin = part.strip().rstrip("/")
            if not origin:
                continue
            if not origin.startswith(("http://", "https://")):
                origin = f"https://{origin}"
            origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()

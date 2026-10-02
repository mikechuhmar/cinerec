from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.config import get_settings
from app.db import async_engine
from app.logging_config import configure_logging, get_logger
from app.observability import setup_metrics, setup_tracing
from app.routers import health, movies, ratings, recommend

configure_logging()
log = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.recsys import collaborative

    # Ensure the pgvector extension exists (tables are managed by Alembic migrations).
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    collaborative.start_retrainer()
    log.info("startup_complete", background_retrain=settings.enable_background_retrain)
    try:
        yield
    finally:
        collaborative.stop_retrainer()
        await async_engine.dispose()
        log.info("shutdown_complete")


app = FastAPI(
    title="cinerec API",
    version="0.1.0",
    description="Movie recommendation system (content-based via pgvector + collaborative ALS).",
    lifespan=lifespan,
)

# Rate limiting (per client IP). slowapi reads limits off app.state.limiter.
_default_limits = [settings.rate_limit] if settings.rate_limit else []
limiter = Limiter(key_func=get_remote_address, default_limits=_default_limits)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    log.warning("rate_limited", path=request.url.path, client=get_remote_address(request))
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Middleware (outermost first): correlation id → CORS → rate limiting.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")

setup_metrics(app)
setup_tracing(app)

app.include_router(health.router)
app.include_router(movies.router)
app.include_router(recommend.router)
app.include_router(ratings.router)


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"name": "cinerec", "docs": "/docs", "health": "/health"}

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from src.config import settings
from src.api.endpoints import router
from src.api.admin import router as admin_router
from src.streaming.publisher import RedisPublisher
from src.streaming.outbox_worker import start_outbox_worker
from src.streaming.consumer import start_redis_consumer
from src.db.models import Base
from src.db.session import engine

# Setup logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from typing import Any

# Dictionary to hold task references to prevent garbage collection and allow clean shutdown
background_tasks: dict[str, asyncio.Task[Any]] = {}


def validate_production_configuration() -> None:
    if not settings.SERVERLESS_MODE:
        return
    errors = []
    if settings.DEMO_MODE: errors.append("DEMO_MODE must be false")
    if not settings.INLINE_PROCESSING: errors.append("INLINE_PROCESSING must be true")
    if settings.DEBUG: errors.append("DEBUG must be false")
    if settings.DATABASE_URL.startswith("sqlite"): errors.append("PostgreSQL DATABASE_URL is required")
    if not settings.DATABASE_URL.startswith(("postgresql", "postgres")): errors.append("DATABASE_URL must use PostgreSQL")
    if not settings.CLERK_ISSUER or not settings.CLERK_JWKS_URL: errors.append("Clerk issuer and JWKS URL are required")
    if not settings.CREDENTIAL_PEPPER: errors.append("CREDENTIAL_PEPPER is required")
    if settings.MANAGER_API_KEY or settings.ADMIN_API_KEY: errors.append("browser/admin shared credentials are prohibited")
    if errors: raise RuntimeError("Invalid serverless production configuration: " + "; ".join(errors))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle application lifecycle events.
    Setup Redis connection, Publisher, and start background workers.
    """
    validate_production_configuration()
    logger.info("Starting up LOSSLine Backend...")

    if settings.DATABASE_URL.startswith("sqlite"):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    redis_client = None
    if not settings.SERVERLESS_MODE and not settings.INLINE_PROCESSING:
        redis_client = Redis.from_url(settings.REDIS_URL)
        app.state.redis = redis_client
        publisher = RedisPublisher(redis_client)
        app.state.publisher = publisher
        background_tasks["outbox_worker"] = asyncio.create_task(
            start_outbox_worker(publisher, interval_seconds=1.0)
        )
        background_tasks["redis_consumer"] = asyncio.create_task(
            start_redis_consumer(redis_client)
        )

    yield

    logger.info("Shutting down LOSSLine Backend...")

    # 4. Cancel background tasks
    for name, task in background_tasks.items():
        logger.info(f"Cancelling background task: {name}")
        task.cancel()

    # Wait for tasks to clean up
    await asyncio.gather(*background_tasks.values(), return_exceptions=True)
    background_tasks.clear()

    # 5. Close Redis connection
    if redis_client is not None:
        await redis_client.aclose()
    logger.info("LOSSLine Backend shutdown complete.")


app = FastAPI(
    title="LOSSLine Backend",
    description="Operational Intelligence System for Restaurants",
    version="1.0",
    lifespan=lifespan,
)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if settings.SERVERLESS_MODE and (
            request.url.path.startswith("/api/v1/demo/") or request.url.path == "/api/v1/ws"
        ):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_REQUEST_BYTES:
            return JSONResponse({"detail": "Request body exceeds 256 KiB limit"}, status_code=413)
        body = await request.body()
        if len(body) > settings.MAX_REQUEST_BYTES:
            return JSONResponse({"detail": "Request body exceeds 256 KiB limit"}, status_code=413)
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware)

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-LOSSLine-Key"],
)

# Include API routes
app.include_router(router)
app.include_router(admin_router)

@app.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
    }


@app.get("/ready")
async def readiness_check():
    """Report whether authoritative storage and the stream are reachable."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    validate_production_configuration()
    if not settings.SERVERLESS_MODE and not settings.INLINE_PROCESSING:
        await app.state.redis.ping()
    return {"status": "ready"}

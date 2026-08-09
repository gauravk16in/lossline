import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text

from src.config import settings
from src.api.endpoints import router
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle application lifecycle events.
    Setup Redis connection, Publisher, and start background workers.
    """
    logger.info("Starting up LOSSLine Backend...")

    if settings.DATABASE_URL.startswith("sqlite"):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    redis_client = None
    if not settings.INLINE_PROCESSING:
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

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For demo / development convenience. Adjust as needed.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

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
    if not settings.INLINE_PROCESSING:
        await app.state.redis.ping()
    return {"status": "ready"}

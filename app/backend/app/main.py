import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings
from app.api.endpoints import router
from app.streaming.publisher import RedisPublisher
from app.streaming.outbox_worker import start_outbox_worker
from app.streaming.consumer import start_redis_consumer

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

    # 1. Initialize Redis connection pool
    redis_client = Redis.from_url(settings.REDIS_URL)
    app.state.redis = redis_client

    # 2. Instantiate Publisher
    publisher = RedisPublisher(redis_client)
    app.state.publisher = publisher

    # 3. Spawn background tasks
    outbox_task = asyncio.create_task(
        start_outbox_worker(publisher, interval_seconds=1.0)
    )
    consumer_task = asyncio.create_task(start_redis_consumer(redis_client))

    # Save references
    background_tasks["outbox_worker"] = outbox_task
    background_tasks["redis_consumer"] = consumer_task

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
    await redis_client.close()
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

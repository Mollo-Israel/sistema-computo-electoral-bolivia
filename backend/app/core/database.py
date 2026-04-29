"""
Database connection managers for MongoDB (Cluster 1 - RRV) and PostgreSQL (Cluster 2 - Oficial).
"""
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text

from app.core.config import settings

mongo_client: AsyncIOMotorClient | None = None
pg_engine: AsyncEngine | None = None


async def connect_mongo() -> AsyncIOMotorClient:
    global mongo_client
    if mongo_client is None:
        mongo_client = AsyncIOMotorClient(
            settings.mongo_rrv_uri,
            serverSelectionTimeoutMS=5000,
            retryWrites=True,
            retryReads=True,
        )
        await mongo_client.admin.command("ping")
    return mongo_client


async def disconnect_mongo() -> None:
    global mongo_client
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None


async def connect_postgres() -> AsyncEngine:
    global pg_engine
    if pg_engine is None:
        database_url = (
            f"postgresql+asyncpg://{settings.postgres_oficial_user}:"
            f"{settings.postgres_oficial_password}@{settings.postgres_oficial_host}:"
            f"{settings.postgres_oficial_port}/{settings.postgres_oficial_db}"
        )
        pg_engine = create_async_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )
        async with pg_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    return pg_engine


async def disconnect_postgres() -> None:
    global pg_engine
    if pg_engine is not None:
        await pg_engine.dispose()
        pg_engine = None

"""
Database connection managers for MongoDB (Cluster 1 - RRV) and PostgreSQL (Cluster 2 - Oficial).
TODO (Escobar): implement replica set connection, connection pooling, and fault tolerance.
"""

# TODO (Escobar): initialize Motor async client for MongoDB RRV cluster
# from motor.motor_asyncio import AsyncIOMotorClient
# mongo_client: AsyncIOMotorClient = None

# TODO (Escobar): initialize asyncpg / SQLAlchemy async engine for PostgreSQL Oficial cluster
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# pg_engine = None


async def connect_mongo():
    # TODO (Escobar): establish MongoDB connection on app startup
    pass


async def disconnect_mongo():
    # TODO (Escobar): close MongoDB connection on app shutdown
    pass


async def connect_postgres():
    # TODO (Escobar): establish PostgreSQL connection on app startup
    pass


async def disconnect_postgres():
    # TODO (Escobar): close PostgreSQL connection on app shutdown
    pass

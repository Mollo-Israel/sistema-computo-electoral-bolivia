"""
Entry point for the Electoral Count System API.
"""
from fastapi import FastAPI

from app.api.health_routes import router as health_router
from app.core.database import (
    connect_mongo,
    connect_postgres,
    disconnect_mongo,
    disconnect_postgres,
)

app = FastAPI(
    title="Sistema de Cómputo Electoral Bolivia",
    version="0.1.0",
    description="API para los pipelines RRV y Cómputo Oficial.",
)

app.include_router(health_router, prefix="/api/health", tags=["Health"])


@app.on_event("startup")
async def startup_event() -> None:
    await connect_mongo()
    await connect_postgres()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await disconnect_mongo()
    await disconnect_postgres()


@app.get("/")
async def root() -> dict:
    return {"message": "Sistema de Cómputo Electoral - API activa"}

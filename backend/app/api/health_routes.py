"""
Health check routes for cluster and service monitoring.
Responsible: Escobar.
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.database import mongo_client, pg_engine

router = APIRouter()


@router.get("/mongo")
async def mongo_health() -> dict:
    if mongo_client is None:
        raise HTTPException(status_code=503, detail="MongoDB connection is not initialized")

    try:
        result = await mongo_client.admin.command("ping")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MongoDB cluster unavailable: {exc}")

    return {"status": "ok", "mongo_ping": result}


@router.get("/postgres")
async def postgres_health() -> dict:
    if pg_engine is None:
        raise HTTPException(status_code=503, detail="PostgreSQL connection is not initialized")

    try:
        async with pg_engine.connect() as conn:
            version = await conn.scalar(text("SELECT version()"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"PostgreSQL cluster unavailable: {exc}")

    return {"status": "ok", "postgres_version": version}


@router.get("/sistema")
async def system_health() -> dict:
    mongo_status = None
    postgres_status = None

    try:
        mongo_status = await mongo_health()
    except HTTPException as exc:
        mongo_status = {"status": "error", "detail": exc.detail}

    try:
        postgres_status = await postgres_health()
    except HTTPException as exc:
        postgres_status = {"status": "error", "detail": exc.detail}

    overall_status = "ok" if mongo_status.get("status") == "ok" and postgres_status.get("status") == "ok" else "degraded"
    return {
        "status": overall_status,
        "mongo": mongo_status,
        "postgres": postgres_status,
    }

"""
Entry point for the Electoral Count System API.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.dashboard_routes import router as dashboard_router
from app.api.oficial_routes import router as oficial_router
from app.core.config import settings
from app.utils.storage_utils import ensure_storage_dir

app = FastAPI(
    title="Sistema de Cómputo Electoral Bolivia",
    version="0.1.0",
    description="API para el pipeline Oficial y dashboard comparativo.",
)

app.include_router(oficial_router, prefix="/api/oficial", tags=["Oficial"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

ensure_storage_dir()
project_root = Path(__file__).resolve().parents[2]
dashboard_dir = project_root / settings.dashboard_dir
if dashboard_dir.exists():
    app.mount("/dashboard-ui", StaticFiles(directory=dashboard_dir, html=True), name="dashboard-ui")


@app.get("/")
async def root():
    return {
        "message": "Sistema de Cómputo Electoral - API activa",
        "dashboard_ui": "/dashboard-ui",
        "api_resumen": "/api/dashboard/resumen",
    }

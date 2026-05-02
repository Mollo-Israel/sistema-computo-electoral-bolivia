"""
Dashboard API routes: comparative data between RRV and official count.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.repositories.dashboard_repository import (
    get_anomalias,
    get_comparativo_rrv_oficial,
    get_estado_actas,
    get_geografia,
    get_metricas_tecnicas,
    get_resumen_votos,
)
from app.utils.response_utils import success_response

router = APIRouter()


@router.get("/resumen")
async def resumen():
    return success_response(await get_resumen_votos())


@router.get("/comparacion")
async def comparacion():
    return success_response(await get_comparativo_rrv_oficial())


@router.get("/estados")
async def estados():
    return success_response(await get_estado_actas())


@router.get("/geografia")
async def geografia():
    return success_response(await get_geografia())


@router.get("/tecnico")
async def tecnico():
    return success_response(await get_metricas_tecnicas())


@router.get("/anomalias")
async def anomalias():
    return success_response(await get_anomalias())

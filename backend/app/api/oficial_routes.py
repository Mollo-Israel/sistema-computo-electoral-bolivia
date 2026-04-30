"""
Official Computation (CO) API routes for the CSV automatizador.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.repositories.postgres_oficial_repository import list_actas_oficiales, list_auditoria
from app.schemas.oficial_schema import ActaOficialBatchInput, ActaOficialInput
from app.services.oficial.oficial_service import procesar_acta_oficial, procesar_actas_oficiales_batch
from app.utils.response_utils import success_response

router = APIRouter()


@router.post("/transcribir")
async def transcribir_acta(payload: ActaOficialInput):
    result = await procesar_acta_oficial(payload.model_dump())
    return success_response(result, "Acta oficial procesada")


@router.post("/importar-csv")
async def importar_csv(payload: ActaOficialBatchInput):
    summary = await procesar_actas_oficiales_batch([acta.model_dump() for acta in payload.actas])
    return success_response(summary, "Lote CSV procesado")


@router.get("/actas")
async def get_actas(
    estado: str | None = Query(default=None),
    departamento: str | None = Query(default=None),
    provincia: str | None = Query(default=None),
    municipio: str | None = Query(default=None),
    usuario_id: int | None = Query(default=None),
):
    data = await list_actas_oficiales(
        {
            "estado": estado,
            "departamento": departamento,
            "provincia": provincia,
            "municipio": municipio,
            "usuario_id": usuario_id,
        }
    )
    return success_response(data)


@router.get("/acta/{mesa_codigo}")
async def get_acta_by_mesa(mesa_codigo: str):
    data = await list_actas_oficiales({"mesa_codigo": mesa_codigo})
    return success_response(data[0] if data else None)


@router.get("/auditoria")
async def get_auditoria(mesa_codigo: str | None = Query(default=None)):
    data = await list_auditoria({"mesa_codigo": mesa_codigo})
    return success_response(data)

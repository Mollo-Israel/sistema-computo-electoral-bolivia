"""
Pydantic schemas for the Official Computation (CO) pipeline.
Field names must match the standard data contract exactly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import EstadoActa


class ActaOficialInput(BaseModel):
    mesa_codigo: str
    codigo_recinto: str
    codigo_territorial: str
    nro_mesa: Optional[int] = None
    recinto_nombre: Optional[str] = None
    departamento: Optional[str] = None
    provincia: Optional[str] = None
    municipio: Optional[str] = None
    partido_1_votos: int
    partido_2_votos: int
    partido_3_votos: int
    partido_4_votos: int
    votos_validos: int
    votos_blancos: int
    votos_nulos: int
    votos_emitidos: int
    boletas_no_utilizadas: int
    total_boletas: int
    nro_votantes: int
    fuente: str = Field(default="AUTOMATIZADOR")
    fila_csv: int
    usuario_id: int


class ActaOficialOutput(ActaOficialInput):
    acta_oficial_id: int
    hash_registro: str
    estado: EstadoActa
    observacion: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    validado_at: Optional[datetime] = None
    publicado_at: Optional[datetime] = None


class ActaOficialBatchInput(BaseModel):
    actas: list[ActaOficialInput]


class AuditoriaRegistro(BaseModel):
    auditoria_id: int
    acta_oficial_id: int
    mesa_codigo: str
    usuario_id: int
    accion: str
    descripcion: str
    valor_anterior: Optional[str] = None
    valor_nuevo: Optional[str] = None
    nodo_cluster: str = "local-json"
    fecha: datetime

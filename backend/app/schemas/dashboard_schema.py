"""
Pydantic schemas for dashboard API responses.
"""
from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel


class ResumenVotos(BaseModel):
    total_mesas: int
    mesas_procesadas: int
    votos_validos: int
    votos_blancos: int
    votos_nulos: int
    votos_emitidos: int
    participacion_porcentaje: float
    votos_por_partido: Dict[str, int]
    porcentaje_por_partido: Dict[str, float]
    margen_victoria: float


class ComparativoRRVOficial(BaseModel):
    mesa_codigo: str
    departamento: Optional[str]
    municipio: Optional[str]
    estado_rrv: Optional[str]
    estado_oficial: Optional[str]
    rrv_votos_validos: Optional[int]
    oficial_votos_validos: Optional[int]
    diferencia: Optional[int]
    coincide_total_boletas: bool
    coincide_votos_emitidos: bool


class MetricasTecnicas(BaseModel):
    latencia_promedio_ms: float
    throughput_actas_por_minuto: float
    disponibilidad_porcentaje: float
    total_actas_procesadas: int


class GeografiaResultado(BaseModel):
    clave: str
    votos_emitidos: int
    votos_validos: int
    actas: int


class AnomaliaRegistro(BaseModel):
    mesa_codigo: str
    fuente: str
    estado: str
    descripcion: str

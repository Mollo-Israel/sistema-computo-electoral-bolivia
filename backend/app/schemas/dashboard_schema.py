"""
Pydantic schemas for dashboard API responses.
TODO (Erick Diaz): define aggregation response shapes.
"""
from pydantic import BaseModel
from typing import Dict, List, Optional


class ResumenVotos(BaseModel):
    total_mesas: int
    mesas_procesadas: int
    votos_validos: int
    votos_blancos: int
    votos_nulos: int
    votos_emitidos: int
    participacion_porcentaje: float
    votos_por_partido: Dict[str, int]
    # TODO (Erick Diaz): add margen_victoria, porcentaje_por_partido


class ComparativoRRVOficial(BaseModel):
    mesa_codigo: str
    rrv_votos_validos: Optional[int]
    oficial_votos_validos: Optional[int]
    diferencia: Optional[int]
    # TODO (Erick Diaz): extend with all partido fields


class MetricasTecnicas(BaseModel):
    latencia_promedio_ms: float
    throughput_actas_por_minuto: float
    disponibilidad_porcentaje: float
    # TODO (Escobar): add cluster-specific metrics

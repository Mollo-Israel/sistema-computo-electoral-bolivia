"""
Pydantic schemas for the RRV pipeline input and output.
Field names must match the standard data contract exactly.
TODO (MOLLO / Ferrufino / Sanabria): complete and validate field constraints.
"""
from pydantic import BaseModel
from typing import Optional
from app.core.constants import EstadoActa, OrigenActa, FuenteActa


class ActaRRVInput(BaseModel):
    mesa_codigo: str
    nro_mesa: int
    codigo_recinto: str
    recinto_nombre: str
    codigo_territorial: str
    departamento: str
    provincia: str
    municipio: str
    origen: OrigenActa
    fuente: FuenteActa
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
    # TODO (MOLLO): add ocr_confidence field for image-based acts
    # ocr_confidence: Optional[float] = None


class ActaRRVOutput(ActaRRVInput):
    estado: EstadoActa
    # TODO (Sanabria): add timestamp, log_id, evento_id fields

"""
Pydantic schemas for the Official Computation (CO) pipeline.
Field names must match the standard data contract exactly.
TODO (Erick Diaz): complete with auditable fields.
"""
from pydantic import BaseModel
from app.core.constants import EstadoActa


class ActaOficialInput(BaseModel):
    mesa_codigo: str
    codigo_recinto: str
    codigo_territorial: str
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
    fuente: str  # always "AUTOMATIZADOR"
    fila_csv: int
    usuario_id: int


class ActaOficialOutput(ActaOficialInput):
    estado: EstadoActa
    # TODO (Erick Diaz): add auditoria_id, timestamp fields

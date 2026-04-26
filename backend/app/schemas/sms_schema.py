"""
Pydantic schemas for SMS-based act ingestion.
TODO (Ferrufino): define SMS format, PIN validation, and parsing rules.
"""
from pydantic import BaseModel


class SMSInput(BaseModel):
    numero_telefono: str
    mensaje_raw: str
    # TODO (Ferrufino): add timestamp, operator, region fields


class SMSParsed(BaseModel):
    mesa_codigo: str
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
    # TODO (Ferrufino): mark as RECHAZADA if format is invalid

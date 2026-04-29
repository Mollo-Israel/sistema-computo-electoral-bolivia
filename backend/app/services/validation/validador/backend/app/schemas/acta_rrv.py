from typing import Optional
from pydantic import BaseModel, Field


class ActaRRVInput(BaseModel):
    """JSON estándar RRV — contrato de entrada al validador."""

    mesa_codigo: str
    nro_mesa: int
    codigo_recinto: str
    recinto_nombre: Optional[str] = None
    codigo_territorial: str
    departamento: Optional[str] = None
    provincia: Optional[str] = None
    municipio: Optional[str] = None

    origen: str = Field(..., pattern="^(OCR|APP|SMS)$")
    fuente: str = Field(..., pattern="^(PDF|IMAGEN|FOTO_MOVIL|SMS)$")

    partido_1_votos: int = Field(..., ge=0)
    partido_2_votos: int = Field(..., ge=0)
    partido_3_votos: int = Field(..., ge=0)
    partido_4_votos: int = Field(..., ge=0)

    votos_validos: int = Field(..., ge=0)
    votos_blancos: int = Field(..., ge=0)
    votos_nulos: int = Field(..., ge=0)
    votos_emitidos: int = Field(..., ge=0)
    boletas_no_utilizadas: int = Field(..., ge=0)
    total_boletas: int = Field(..., ge=0)
    nro_votantes: int = Field(..., ge=0)

    # Campos OCR
    confianza_ocr: Optional[float] = None
    calidad_imagen: Optional[str] = None  # BUENA | REGULAR | MALA

    # Campos SMS
    parser_estado: Optional[str] = None  # OK | INVALIDO | ERROR_FORMATO
    pin_recibido: Optional[str] = None
    telefono_origen: Optional[str] = None

    # IDs previos (idempotencia)
    acta_rrv_id: Optional[str] = None

from typing import Optional
from pydantic import BaseModel, Field


class ActaOficialInput(BaseModel):
    """JSON estándar Cómputo Oficial — contrato de entrada al validador oficial."""

    mesa_codigo: str
    codigo_recinto: str
    codigo_territorial: str

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

    fuente: str = Field(..., pattern="^(CSV_OFICIAL|FORMULARIO|AUTOMATIZADOR)$")
    fila_csv: Optional[int] = None
    usuario_id: int

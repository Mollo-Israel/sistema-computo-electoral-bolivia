from typing import List, Optional
from pydantic import BaseModel


class ValidationResponse(BaseModel):
    """Respuesta estándar del validador (RRV y Oficial)."""

    estado: str
    motivo_observacion: Optional[str] = None
    errores: List[str] = []

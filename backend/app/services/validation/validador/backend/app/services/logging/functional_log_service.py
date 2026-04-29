"""
Servicio de logs funcionales — registra errores de negocio, no logs técnicos.

Ejemplos de uso:
  - Acta duplicada
  - Total de votos incoherente
  - Imagen ilegible / OCR con baja confianza
  - SMS con formato inválido
  - Mesa inexistente
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ── Enumeraciones ─────────────────────────────────────────────────────────────

class TipoLog(str, Enum):
    DUPLICADO = "DUPLICADO"
    TOTAL_NO_COINCIDE = "TOTAL_NO_COINCIDE"
    INCOHERENCIA_NUMERICA = "INCOHERENCIA_NUMERICA"
    OCR_BAJA_CONFIANZA = "OCR_BAJA_CONFIANZA"
    IMAGEN_ILEGIBLE = "IMAGEN_ILEGIBLE"
    SMS_FORMATO_INVALIDO = "SMS_FORMATO_INVALIDO"
    SMS_NO_AUTORIZADO = "SMS_NO_AUTORIZADO"
    MESA_NO_EXISTE = "MESA_NO_EXISTE"
    VOTOS_EXCEDEN_HABILITADOS = "VOTOS_EXCEDEN_HABILITADOS"
    ERROR_SISTEMA = "ERROR_SISTEMA"


class NivelLog(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ── Mapa motivo → (tipo, nivel) ───────────────────────────────────────────────

_MOTIVO_MAP: dict[str, tuple[TipoLog, NivelLog]] = {
    "DUPLICADO":                (TipoLog.DUPLICADO,                NivelLog.WARNING),
    "TOTAL_NO_COINCIDE":        (TipoLog.TOTAL_NO_COINCIDE,        NivelLog.ERROR),
    "INCOHERENCIA_NUMERICA":    (TipoLog.INCOHERENCIA_NUMERICA,    NivelLog.ERROR),
    "OCR_BAJA_CONFIANZA":       (TipoLog.OCR_BAJA_CONFIANZA,       NivelLog.WARNING),
    "IMAGEN_ILEGIBLE":          (TipoLog.IMAGEN_ILEGIBLE,          NivelLog.ERROR),
    "SMS_FORMATO_INVALIDO":     (TipoLog.SMS_FORMATO_INVALIDO,     NivelLog.ERROR),
    "SMS_NO_AUTORIZADO":        (TipoLog.SMS_NO_AUTORIZADO,        NivelLog.CRITICAL),
    "MESA_NO_EXISTE":           (TipoLog.MESA_NO_EXISTE,           NivelLog.ERROR),
    "VOTOS_EXCEDEN_HABILITADOS":(TipoLog.VOTOS_EXCEDEN_HABILITADOS,NivelLog.CRITICAL),
    "ERROR_SISTEMA":            (TipoLog.ERROR_SISTEMA,            NivelLog.CRITICAL),
}

_ACCION_POR_ESTADO: dict[str, str] = {
    "VALIDADA":  "Acta aprobada y lista para persistir",
    "OBSERVADA": "Acta marcada como OBSERVADA; requiere revisión manual",
    "RECHAZADA": "Acta RECHAZADA; no se persiste en la base de datos",
    "DUPLICADA": "Acta marcada como DUPLICADA; la original no fue reemplazada",
}


# ── Modelo de log ─────────────────────────────────────────────────────────────

@dataclass
class LogEntry:
    log_id: str
    acta_rrv_id: Optional[str]
    mesa_codigo: Optional[str]
    tipo: str
    nivel: str
    mensaje: str
    detalle: str
    accion_tomada: str
    fecha: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Servicio ──────────────────────────────────────────────────────────────────

class FunctionalLogService:
    """
    Crea entradas de log funcional a partir de resultados de validación.

    Inyectar `logs_repository` (con método `save(doc: dict)`) para persistir
    los logs en MongoDB (colección rrv_logs).
    """

    def __init__(self, logs_repository=None):
        self._repo = logs_repository

    def log_from_validation(
        self,
        validation_result: Any,
        acta_rrv_id: Optional[str] = None,
        mesa_codigo: Optional[str] = None,
    ) -> Optional[LogEntry]:
        """
        Genera un log a partir de un ValidationResult.
        Retorna None si el acta es VALIDADA (no hay nada que registrar).
        """
        motivo: Optional[str] = getattr(validation_result, "motivo_observacion", None)
        estado_raw = getattr(validation_result, "estado", None)
        estado: str = estado_raw.value if hasattr(estado_raw, "value") else str(estado_raw)

        if estado == "VALIDADA" or motivo is None:
            return None

        tipo, nivel = _MOTIVO_MAP.get(motivo, (TipoLog.ERROR_SISTEMA, NivelLog.ERROR))
        errores: list = getattr(validation_result, "errores", [])
        detalle = "; ".join(errores) if errores else motivo
        accion = _ACCION_POR_ESTADO.get(estado, f"Estado asignado: {estado}")

        entry = LogEntry(
            log_id=str(uuid.uuid4()),
            acta_rrv_id=acta_rrv_id,
            mesa_codigo=mesa_codigo,
            tipo=tipo.value,
            nivel=nivel.value,
            mensaje=accion,
            detalle=detalle,
            accion_tomada=accion,
            fecha=datetime.now(timezone.utc).isoformat(),
        )

        if self._repo:
            self._repo.save(entry.to_dict())

        return entry

    def log_mesa_no_existe(
        self,
        mesa_codigo: str,
        acta_rrv_id: Optional[str] = None,
    ) -> LogEntry:
        """Registra cuando una mesa_codigo no existe en el catálogo."""
        entry = LogEntry(
            log_id=str(uuid.uuid4()),
            acta_rrv_id=acta_rrv_id,
            mesa_codigo=mesa_codigo,
            tipo=TipoLog.MESA_NO_EXISTE.value,
            nivel=NivelLog.ERROR.value,
            mensaje=f"La mesa '{mesa_codigo}' no existe en el catálogo de mesas",
            detalle="Verificar código de mesa en el sistema de registro electoral",
            accion_tomada="Acta marcada como OBSERVADA; requiere corrección del código",
            fecha=datetime.now(timezone.utc).isoformat(),
        )
        if self._repo:
            self._repo.save(entry.to_dict())
        return entry

    def log_error_sistema(
        self,
        mensaje: str,
        acta_rrv_id: Optional[str] = None,
        mesa_codigo: Optional[str] = None,
        detalle: str = "",
    ) -> LogEntry:
        """Registra un error interno inesperado del sistema."""
        entry = LogEntry(
            log_id=str(uuid.uuid4()),
            acta_rrv_id=acta_rrv_id,
            mesa_codigo=mesa_codigo,
            tipo=TipoLog.ERROR_SISTEMA.value,
            nivel=NivelLog.CRITICAL.value,
            mensaje=mensaje,
            detalle=detalle or "Error interno; revisar trazas del servidor",
            accion_tomada="Acta no procesada; error registrado para revisión",
            fecha=datetime.now(timezone.utc).isoformat(),
        )
        if self._repo:
            self._repo.save(entry.to_dict())
        return entry

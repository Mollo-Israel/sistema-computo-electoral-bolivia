"""
Validador RRV — aplica reglas OEP al flujo de Recuento Rápido de Votos.

Maneja los tres orígenes posibles: OCR, APP y SMS.
Retorna un ValidationResult con estado, motivo_observacion y lista de errores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .validation_rules import run_all_rules


# ── Enumeraciones ─────────────────────────────────────────────────────────────

class EstadoActaRRV(str, Enum):
    RECIBIDA = "RECIBIDA"
    PROCESANDO = "PROCESANDO"
    VALIDADA = "VALIDADA"
    OBSERVADA = "OBSERVADA"
    RECHAZADA = "RECHAZADA"
    DUPLICADA = "DUPLICADA"
    PUBLICADA = "PUBLICADA"


class MotivoObservacion(str, Enum):
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


# ── Resultado de validación ───────────────────────────────────────────────────

@dataclass
class ValidationResult:
    estado: EstadoActaRRV
    motivo_observacion: Optional[str] = None
    errores: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "estado": self.estado.value,
            "motivo_observacion": self.motivo_observacion,
            "errores": self.errores,
        }

    @property
    def es_valida(self) -> bool:
        return self.estado == EstadoActaRRV.VALIDADA


# ── Validador RRV ─────────────────────────────────────────────────────────────

class RRVValidator:
    """
    Valida un acta RRV aplicando las reglas OEP.

    Inyectar `actas_repository` (con método `existe_acta_valida(mesa_codigo)`)
    para activar la detección de duplicados contra la base de datos.
    """

    OCR_CONFIANZA_MINIMA: float = 0.75

    def __init__(self, actas_repository=None):
        self._repo = actas_repository

    # ── Punto de entrada principal ────────────────────────────────────────────

    def validate(self, data: dict) -> ValidationResult:
        """Valida el JSON estándar RRV y devuelve un ValidationResult."""

        # 1. Duplicado (prioridad máxima — no reemplazar automáticamente)
        if self._es_duplicada(data):
            return ValidationResult(
                estado=EstadoActaRRV.DUPLICADA,
                motivo_observacion=MotivoObservacion.DUPLICADO.value,
                errores=["Ya existe un acta válida o publicada para esta mesa"],
            )

        # 2. Validaciones específicas por origen
        origen = data.get("origen", "")
        if origen == "SMS":
            result = self._check_sms(data)
            if not result.es_valida:
                return result

        if origen == "OCR":
            result = self._check_ocr(data)
            if not result.es_valida:
                return result

        # 3. Reglas numéricas OEP
        ok, errores = run_all_rules(data)
        if not ok:
            motivo = self._motivo_numerico(errores)
            return ValidationResult(
                estado=EstadoActaRRV.OBSERVADA,
                motivo_observacion=motivo,
                errores=errores,
            )

        return ValidationResult(estado=EstadoActaRRV.VALIDADA)

    # ── Checks privados ───────────────────────────────────────────────────────

    def _es_duplicada(self, data: dict) -> bool:
        if not self._repo:
            return False
        mesa_codigo = data.get("mesa_codigo")
        return bool(mesa_codigo and self._repo.existe_acta_valida(mesa_codigo))

    def _check_sms(self, data: dict) -> ValidationResult:
        """Regla 7 — SMS con formato inválido o PIN no autorizado → RECHAZADA."""
        parser_estado = data.get("parser_estado", "")
        if parser_estado in ("INVALIDO", "ERROR_FORMATO"):
            return ValidationResult(
                estado=EstadoActaRRV.RECHAZADA,
                motivo_observacion=MotivoObservacion.SMS_FORMATO_INVALIDO.value,
                errores=["SMS con formato inválido; no se pudo interpretar el mensaje"],
            )
        if parser_estado == "PIN_INVALIDO":
            return ValidationResult(
                estado=EstadoActaRRV.RECHAZADA,
                motivo_observacion=MotivoObservacion.SMS_NO_AUTORIZADO.value,
                errores=["PIN del SMS no autorizado o no coincide con el registrado"],
            )
        return ValidationResult(estado=EstadoActaRRV.VALIDADA)

    def _check_ocr(self, data: dict) -> ValidationResult:
        """Reglas 6a/6b — imagen ilegible o confianza OCR baja → OBSERVADA."""
        calidad = data.get("calidad_imagen", "BUENA")
        if calidad == "MALA":
            return ValidationResult(
                estado=EstadoActaRRV.OBSERVADA,
                motivo_observacion=MotivoObservacion.IMAGEN_ILEGIBLE.value,
                errores=["La calidad de la imagen es insuficiente para una extracción confiable"],
            )

        confianza = data.get("confianza_ocr")
        if confianza is not None and float(confianza) < self.OCR_CONFIANZA_MINIMA:
            return ValidationResult(
                estado=EstadoActaRRV.OBSERVADA,
                motivo_observacion=MotivoObservacion.OCR_BAJA_CONFIANZA.value,
                errores=[
                    f"Confianza OCR {float(confianza):.0%} es menor al umbral mínimo "
                    f"{self.OCR_CONFIANZA_MINIMA:.0%}"
                ],
            )
        return ValidationResult(estado=EstadoActaRRV.VALIDADA)

    @staticmethod
    def _motivo_numerico(errores: List[str]) -> str:
        """Determina el motivo de observación más relevante según los errores."""
        joined = " ".join(errores).lower()
        if "nro_votantes" in joined:
            return MotivoObservacion.VOTOS_EXCEDEN_HABILITADOS.value
        if "total_boletas" in joined:
            return MotivoObservacion.TOTAL_NO_COINCIDE.value
        return MotivoObservacion.INCOHERENCIA_NUMERICA.value

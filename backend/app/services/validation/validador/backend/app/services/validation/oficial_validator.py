"""
Validador Oficial — aplica reglas OEP al flujo de Cómputo Oficial.

Más estricto que el RRV: exige todos los campos obligatorios, no tolera
campos faltantes y requiere fuente y usuario válidos.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from .validation_rules import run_all_rules
from .rrv_validator import MotivoObservacion, ValidationResult


# ── Estado específico del flujo oficial ──────────────────────────────────────

class EstadoActaOficial(str, Enum):
    TRANSCRITA = "TRANSCRITA"
    VALIDADA = "VALIDADA"
    OBSERVADA = "OBSERVADA"
    APROBADA = "APROBADA"
    PUBLICADA = "PUBLICADA"
    DUPLICADA = "DUPLICADA"


# ── Validador Oficial ─────────────────────────────────────────────────────────

class OficialValidator:
    """
    Valida el JSON estándar del Cómputo Oficial antes de persistirlo.

    Inyectar `actas_repository` (con método `existe_acta_valida(mesa_codigo)`)
    para activar la detección de duplicados.
    """

    CAMPOS_REQUERIDOS: List[str] = [
        "mesa_codigo",
        "codigo_recinto",
        "codigo_territorial",
        "partido_1_votos",
        "partido_2_votos",
        "partido_3_votos",
        "partido_4_votos",
        "votos_validos",
        "votos_blancos",
        "votos_nulos",
        "votos_emitidos",
        "boletas_no_utilizadas",
        "total_boletas",
        "nro_votantes",
        "fuente",
        "usuario_id",
    ]

    FUENTES_VALIDAS = {"CSV_OFICIAL", "FORMULARIO", "AUTOMATIZADOR"}

    def __init__(self, actas_repository=None):
        self._repo = actas_repository

    # ── Punto de entrada principal ────────────────────────────────────────────

    def validate(self, data: dict) -> ValidationResult:
        """Valida el JSON oficial y devuelve un ValidationResult."""

        # 1. Campos obligatorios presentes
        faltantes = [f for f in self.CAMPOS_REQUERIDOS if data.get(f) is None]
        if faltantes:
            return ValidationResult(
                estado=EstadoActaOficial.OBSERVADA,  # type: ignore[arg-type]
                motivo_observacion=MotivoObservacion.INCOHERENCIA_NUMERICA.value,
                errores=[f"Campos obligatorios faltantes: {', '.join(faltantes)}"],
            )

        # 2. Fuente válida
        fuente = data.get("fuente", "")
        if fuente not in self.FUENTES_VALIDAS:
            return ValidationResult(
                estado=EstadoActaOficial.OBSERVADA,  # type: ignore[arg-type]
                motivo_observacion=MotivoObservacion.ERROR_SISTEMA.value,
                errores=[f"Fuente '{fuente}' no es válida; se esperaba: {self.FUENTES_VALIDAS}"],
            )

        # 3. Duplicado
        if self._es_duplicada(data):
            return ValidationResult(
                estado=EstadoActaOficial.DUPLICADA,  # type: ignore[arg-type]
                motivo_observacion=MotivoObservacion.DUPLICADO.value,
                errores=["Ya existe un acta oficial validada o publicada para esta mesa"],
            )

        # 4. Reglas numéricas OEP
        ok, errores = run_all_rules(data)
        if not ok:
            motivo = self._motivo_numerico(errores)
            return ValidationResult(
                estado=EstadoActaOficial.OBSERVADA,  # type: ignore[arg-type]
                motivo_observacion=motivo,
                errores=errores,
            )

        return ValidationResult(estado=EstadoActaOficial.VALIDADA)  # type: ignore[arg-type]

    # ── Checks privados ───────────────────────────────────────────────────────

    def _es_duplicada(self, data: dict) -> bool:
        if not self._repo:
            return False
        mesa_codigo = data.get("mesa_codigo")
        return bool(mesa_codigo and self._repo.existe_acta_valida(mesa_codigo))

    @staticmethod
    def _motivo_numerico(errores: List[str]) -> str:
        joined = " ".join(errores).lower()
        if "nro_votantes" in joined:
            return MotivoObservacion.VOTOS_EXCEDEN_HABILITADOS.value
        if "total_boletas" in joined:
            return MotivoObservacion.TOTAL_NO_COINCIDE.value
        return MotivoObservacion.INCOHERENCIA_NUMERICA.value

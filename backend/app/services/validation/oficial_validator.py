"""
Validates Official Computation acts from the CSV automatizador.
Responsible: Erick Diaz / Sanabria.
"""
from __future__ import annotations

from app.core.constants import EstadoActa
from app.services.validation.validation_rules import (
    rule_nro_votantes,
    rule_total_boletas,
    rule_votos_emitidos,
    rule_votos_validos,
)


async def validate_oficial_acta(data: dict, existing_acta: dict | None = None) -> dict:
    errors: list[str] = []

    numeric_fields = (
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
    )
    negative_fields = [field for field in numeric_fields if data.get(field, 0) < 0]
    if negative_fields:
        errors.append("Se detectaron valores negativos en: " + ", ".join(negative_fields) + ".")

    if not rule_votos_validos(data):
        errors.append("La suma de votos por partido no coincide con votos_validos.")
    if not rule_votos_emitidos(data):
        errors.append("votos_validos + votos_blancos + votos_nulos no coincide con votos_emitidos.")
    if not rule_total_boletas(data):
        errors.append("votos_emitidos + boletas_no_utilizadas no coincide con total_boletas.")
    if not rule_nro_votantes(data):
        errors.append("votos_emitidos excede nro_votantes.")

    if existing_acta:
        changed_fields = []
        for field in (
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
        ):
            if existing_acta.get(field) != data.get(field):
                changed_fields.append(field)
        if changed_fields:
            errors.append(
                "Ya existe una acta para esta mesa con datos distintos. Campos diferentes: "
                + ", ".join(changed_fields)
            )

    estado = EstadoActa.PUBLICADA if not errors else EstadoActa.OBSERVADA
    return {"valid": not errors, "estado": estado, "errores": errors}

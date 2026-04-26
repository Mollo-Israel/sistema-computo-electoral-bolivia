"""
OEP electoral act validation rules.
Responsible: Sanabria.
All rules are documented in docs/reglas_validacion.md.
TODO (Sanabria): implement each rule and return structured validation errors.
"""


def rule_votos_validos(data: dict) -> bool:
    # partido_1_votos + partido_2_votos + partido_3_votos + partido_4_votos == votos_validos
    total = (data["partido_1_votos"] + data["partido_2_votos"] +
             data["partido_3_votos"] + data["partido_4_votos"])
    return total == data["votos_validos"]


def rule_votos_emitidos(data: dict) -> bool:
    # votos_validos + votos_blancos + votos_nulos == votos_emitidos
    total = data["votos_validos"] + data["votos_blancos"] + data["votos_nulos"]
    return total == data["votos_emitidos"]


def rule_total_boletas(data: dict) -> bool:
    # votos_emitidos + boletas_no_utilizadas == total_boletas
    return data["votos_emitidos"] + data["boletas_no_utilizadas"] == data["total_boletas"]


def rule_nro_votantes(data: dict) -> bool:
    # votos_emitidos <= nro_votantes
    return data["votos_emitidos"] <= data["nro_votantes"]


# TODO (Sanabria): rule_no_duplicado — reject if mesa_codigo already has PUBLICADA act
# TODO (Sanabria): rule_ocr_confidence — mark OBSERVADA if OCR confidence below threshold
# TODO (Sanabria): rule_sms_format — mark RECHAZADA if SMS format is invalid

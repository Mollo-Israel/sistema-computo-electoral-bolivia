"""
Reglas de validación OEP — lógica pura sin dependencias de framework.

Cada función recibe un dict con los campos del acta y devuelve (ok: bool, mensaje: str).
"""

from typing import Tuple


def check_votos_por_partido(data: dict) -> Tuple[bool, str]:
    """Regla 1: suma de votos por partido debe igualar votos_validos."""
    p1 = data.get("partido_1_votos", 0)
    p2 = data.get("partido_2_votos", 0)
    p3 = data.get("partido_3_votos", 0)
    p4 = data.get("partido_4_votos", 0)
    esperado = data.get("votos_validos")

    if esperado is None:
        return False, "votos_validos es requerido"

    suma = p1 + p2 + p3 + p4
    if suma != esperado:
        return (
            False,
            f"partido_1+2+3+4 ({suma}) != votos_validos ({esperado})",
        )
    return True, ""


def check_votos_emitidos(data: dict) -> Tuple[bool, str]:
    """Regla 2: votos_validos + votos_blancos + votos_nulos debe igualar votos_emitidos."""
    vv = data.get("votos_validos", 0)
    vb = data.get("votos_blancos", 0)
    vn = data.get("votos_nulos", 0)
    esperado = data.get("votos_emitidos")

    if esperado is None:
        return False, "votos_emitidos es requerido"

    suma = vv + vb + vn
    if suma != esperado:
        return (
            False,
            f"votos_validos+blancos+nulos ({suma}) != votos_emitidos ({esperado})",
        )
    return True, ""


def check_total_boletas(data: dict) -> Tuple[bool, str]:
    """Regla 3: votos_emitidos + boletas_no_utilizadas debe igualar total_boletas."""
    ve = data.get("votos_emitidos", 0)
    bnu = data.get("boletas_no_utilizadas", 0)
    esperado = data.get("total_boletas")

    if esperado is None:
        return False, "total_boletas es requerido"

    suma = ve + bnu
    if suma != esperado:
        return (
            False,
            f"votos_emitidos+boletas_no_utilizadas ({suma}) != total_boletas ({esperado})",
        )
    return True, ""


def check_limite_votantes(data: dict) -> Tuple[bool, str]:
    """Regla 4: votos_emitidos no puede superar nro_votantes habilitados."""
    ve = data.get("votos_emitidos", 0)
    nv = data.get("nro_votantes")

    if nv is None:
        return False, "nro_votantes es requerido"

    if ve > nv:
        return (
            False,
            f"votos_emitidos ({ve}) > nro_votantes ({nv})",
        )
    return True, ""


def run_all_rules(data: dict) -> Tuple[bool, list]:
    """Ejecuta las cuatro reglas numéricas y retorna (todo_ok, lista_de_errores)."""
    errores = []
    for check in (
        check_votos_por_partido,
        check_votos_emitidos,
        check_total_boletas,
        check_limite_votantes,
    ):
        ok, msg = check(data)
        if not ok:
            errores.append(msg)
    return len(errores) == 0, errores

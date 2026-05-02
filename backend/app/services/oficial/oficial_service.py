"""
Orchestrates the Official Computation pipeline: validate, persist and audit.
"""
from __future__ import annotations

from app.core.constants import EstadoActa
from app.repositories.postgres_oficial_repository import (
    get_acta_oficial_by_hash,
    get_acta_oficial_by_mesa,
    load_all_storage,
    overwrite_storage,
    save_acta_oficial,
    save_auditoria,
)
from app.services.validation.oficial_validator import validate_oficial_acta
from app.utils.date_utils import now_bolivia
from app.utils.hash_utils import hash_acta


HASH_FIELDS = (
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
)


def _build_hash(payload: dict) -> str:
    return hash_acta({key: payload.get(key) for key in HASH_FIELDS})


async def procesar_acta_oficial(data: dict) -> dict:
    now = now_bolivia()
    payload = dict(data)
    payload["hash_registro"] = _build_hash(payload)

    existing_by_hash = await get_acta_oficial_by_hash(payload["hash_registro"])
    if existing_by_hash:
        return {
            "duplicate_request": True,
            "acta": existing_by_hash,
            "errores": [],
        }

    existing_by_mesa = await get_acta_oficial_by_mesa(payload["mesa_codigo"])
    validation = await validate_oficial_acta(payload, existing_by_mesa)

    payload["estado"] = validation["estado"].value
    payload["observacion"] = "; ".join(validation["errores"]) if validation["errores"] else None
    payload["created_at"] = now.isoformat()
    payload["updated_at"] = now.isoformat()
    payload["validado_at"] = now.isoformat()
    payload["publicado_at"] = now.isoformat() if validation["estado"] == EstadoActa.PUBLICADA else None

    acta_id = await save_acta_oficial(payload)
    payload["acta_oficial_id"] = acta_id

    await save_auditoria(
        {
            "acta_oficial_id": acta_id,
            "mesa_codigo": payload["mesa_codigo"],
            "usuario_id": payload["usuario_id"],
            "accion": "PUBLICAR" if validation["valid"] else "OBSERVAR",
            "descripcion": "Carga desde automatizador oficial",
            "valor_anterior": None if not existing_by_mesa else existing_by_mesa.get("hash_registro"),
            "valor_nuevo": payload["hash_registro"],
            "nodo_cluster": "local-json",
            "fecha": now.isoformat(),
        }
    )

    return {
        "duplicate_request": False,
        "acta": payload,
        "errores": validation["errores"],
    }


async def procesar_actas_oficiales_batch(actas: list[dict]) -> dict:
    stored_actas, stored_auditoria = await load_all_storage()
    by_hash = {acta.get("hash_registro"): acta for acta in stored_actas}
    by_mesa = {acta.get("mesa_codigo"): acta for acta in stored_actas}

    next_acta_id = len(stored_actas) + 1
    next_auditoria_id = len(stored_auditoria) + 1

    summary = {
        "total": len(actas),
        "publicadas": 0,
        "observadas": 0,
        "duplicadas_hash": 0,
        "errores": 0,
    }

    for input_acta in actas:
        now = now_bolivia()
        payload = dict(input_acta)
        payload["hash_registro"] = _build_hash(payload)

        existing_by_hash = by_hash.get(payload["hash_registro"])
        if existing_by_hash:
            summary["duplicadas_hash"] += 1
            continue

        existing_by_mesa = by_mesa.get(payload["mesa_codigo"])
        validation = await validate_oficial_acta(payload, existing_by_mesa)

        payload["estado"] = validation["estado"].value
        payload["observacion"] = "; ".join(validation["errores"]) if validation["errores"] else None
        payload["created_at"] = now.isoformat()
        payload["updated_at"] = now.isoformat()
        payload["validado_at"] = now.isoformat()
        payload["publicado_at"] = now.isoformat() if validation["estado"] == EstadoActa.PUBLICADA else None
        payload["acta_oficial_id"] = next_acta_id
        next_acta_id += 1

        stored_actas.append(payload)
        by_hash[payload["hash_registro"]] = payload
        by_mesa[payload["mesa_codigo"]] = payload

        stored_auditoria.append(
            {
                "auditoria_id": next_auditoria_id,
                "acta_oficial_id": payload["acta_oficial_id"],
                "mesa_codigo": payload["mesa_codigo"],
                "usuario_id": payload["usuario_id"],
                "accion": "PUBLICAR" if validation["valid"] else "OBSERVAR",
                "descripcion": "Carga desde automatizador oficial",
                "valor_anterior": None if not existing_by_mesa else existing_by_mesa.get("hash_registro"),
                "valor_nuevo": payload["hash_registro"],
                "nodo_cluster": "local-json",
                "fecha": now.isoformat(),
            }
        )
        next_auditoria_id += 1

        if validation["estado"] == EstadoActa.PUBLICADA:
            summary["publicadas"] += 1
        else:
            summary["observadas"] += 1
        if validation["errores"]:
            summary["errores"] += len(validation["errores"])

    await overwrite_storage(stored_actas, stored_auditoria)
    return summary

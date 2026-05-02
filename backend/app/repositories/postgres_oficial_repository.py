"""
Local persistence layer for the Official Computation pipeline.
This replaces the placeholder PostgreSQL repository until the shared cluster is ready.
"""
from __future__ import annotations

from app.utils.storage_utils import read_json_file, write_json_file

ACTAS_FILE = "oficial_actas.json"
AUDITORIA_FILE = "auditoria_oficial.json"


def _load_actas() -> list[dict]:
    return read_json_file(ACTAS_FILE, [])


def _save_actas(actas: list[dict]) -> None:
    write_json_file(ACTAS_FILE, actas)


def _load_auditoria() -> list[dict]:
    return read_json_file(AUDITORIA_FILE, [])


def _save_auditoria(registros: list[dict]) -> None:
    write_json_file(AUDITORIA_FILE, registros)


async def load_all_storage() -> tuple[list[dict], list[dict]]:
    return _load_actas(), _load_auditoria()


async def overwrite_storage(actas: list[dict], auditoria: list[dict]) -> None:
    _save_actas(actas)
    _save_auditoria(auditoria)


async def save_acta_oficial(acta: dict) -> int:
    actas = _load_actas()
    acta_id = len(actas) + 1
    acta["acta_oficial_id"] = acta_id
    actas.append(acta)
    _save_actas(actas)
    return acta_id


async def get_acta_oficial_by_mesa(mesa_codigo: str) -> dict | None:
    actas = _load_actas()
    for acta in reversed(actas):
        if acta.get("mesa_codigo") == mesa_codigo:
            return acta
    return None


async def get_acta_oficial_by_hash(hash_registro: str) -> dict | None:
    actas = _load_actas()
    for acta in reversed(actas):
        if acta.get("hash_registro") == hash_registro:
            return acta
    return None


async def list_actas_oficiales(filtros: dict) -> list:
    actas = _load_actas()
    results = actas

    for key in ("estado", "departamento", "provincia", "municipio", "mesa_codigo", "usuario_id"):
        value = filtros.get(key)
        if value in (None, ""):
            continue
        results = [acta for acta in results if str(acta.get(key, "")).lower() == str(value).lower()]

    return results


async def save_auditoria(registro: dict) -> int:
    registros = _load_auditoria()
    auditoria_id = len(registros) + 1
    registro["auditoria_id"] = auditoria_id
    registros.append(registro)
    _save_auditoria(registros)
    return auditoria_id


async def list_auditoria(filtros: dict) -> list[dict]:
    registros = _load_auditoria()
    if filtros.get("mesa_codigo"):
        registros = [row for row in registros if row.get("mesa_codigo") == filtros["mesa_codigo"]]
    return registros

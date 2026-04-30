from __future__ import annotations

import csv
import math
from pathlib import Path

import pandas as pd


FIELD_ALIASES = {
    "mesa_codigo": "mesa_codigo",
    "codigo_recinto": "codigo_recinto",
    "codigo_territorial": "codigo_territorial",
    "nro_mesa": "nro_mesa",
    "recinto_nombre": "recinto_nombre",
    "departamento": "departamento",
    "provincia": "provincia",
    "municipio": "municipio",
    "partido_1_votos": "partido_1_votos",
    "partido_2_votos": "partido_2_votos",
    "partido_3_votos": "partido_3_votos",
    "partido_4_votos": "partido_4_votos",
    "votos_validos": "votos_validos",
    "votos_blancos": "votos_blancos",
    "votos_nulos": "votos_nulos",
    "votos_emitidos": "votos_emitidos",
    "boletas_no_utilizadas": "boletas_no_utilizadas",
    "total_boletas": "total_boletas",
    "nro_votantes": "nro_votantes",
    "usuario_id": "usuario_id",
}

INT_FIELDS = {
    "nro_mesa",
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
    "usuario_id",
}


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _clean_text(value) -> str | None:
    if _is_empty(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _normalize_row(row: dict, row_index: int, default_usuario_id: int | None = None) -> dict:
    mapped = {"fuente": "AUTOMATIZADOR", "fila_csv": row_index}
    for source_key, target_key in FIELD_ALIASES.items():
        value = row.get(source_key, "")
        if target_key in INT_FIELDS:
            mapped[target_key] = int(value) if not _is_empty(value) else 0
        else:
            mapped[target_key] = _clean_text(value)

    if default_usuario_id is not None and not mapped.get("usuario_id"):
        mapped["usuario_id"] = default_usuario_id

    return mapped


def load_csv_rows(csv_path: str | Path, default_usuario_id: int | None = None) -> list[dict]:
    path = Path(csv_path)
    rows: list[dict] = []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row_index, row in enumerate(reader, start=2):
            rows.append(_normalize_row(row, row_index, default_usuario_id))

    return rows


def load_excel_rows(
    excel_path: str | Path,
    sheet_name: str = "Transcripciones",
    default_usuario_id: int | None = None,
) -> list[dict]:
    path = Path(excel_path)
    df = pd.read_excel(path, sheet_name=sheet_name)
    rows: list[dict] = []

    for row_index, record in enumerate(df.to_dict(orient="records"), start=2):
        codigo_recinto = _clean_text(record.get("CodigoRecinto")) or ""
        nro_mesa = int(record.get("NroMesa")) if not _is_empty(record.get("NroMesa")) else 0
        mapped_source = {
            "mesa_codigo": f"{codigo_recinto}-{nro_mesa}",
            "codigo_recinto": codigo_recinto,
            "codigo_territorial": _clean_text(record.get("CodigoTerritorial")),
            "nro_mesa": nro_mesa,
            "recinto_nombre": record.get("RecintoNombre"),
            "departamento": record.get("Departamento"),
            "provincia": record.get("Provincia"),
            "municipio": record.get("Municipio"),
            "partido_1_votos": record.get("P1"),
            "partido_2_votos": record.get("P2"),
            "partido_3_votos": record.get("P3"),
            "partido_4_votos": record.get("P4"),
            "votos_validos": record.get("VotosValidos"),
            "votos_blancos": record.get("VotosBlancos"),
            "votos_nulos": record.get("VotosNulos"),
            "votos_emitidos": record.get("PapeletasAnfora"),
            "boletas_no_utilizadas": record.get("PapeltasNoUtilizadas"),
            "total_boletas": (record.get("PapeletasAnfora") or 0) + (record.get("PapeltasNoUtilizadas") or 0),
            "nro_votantes": record.get("VotantesHabilitados"),
            "usuario_id": default_usuario_id or 4,
        }
        rows.append(_normalize_row(mapped_source, row_index, default_usuario_id))

    return rows


def load_rows(input_path: str | Path, default_usuario_id: int | None = None) -> list[dict]:
    path = Path(input_path)
    if path.suffix.lower() == ".csv":
        return load_csv_rows(path, default_usuario_id=default_usuario_id)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return load_excel_rows(path, default_usuario_id=default_usuario_id)
    raise ValueError(f"Formato no soportado: {path.suffix}")

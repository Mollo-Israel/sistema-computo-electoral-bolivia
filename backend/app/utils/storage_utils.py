"""
Lightweight JSON-file persistence helpers used by the local demo implementation.
These utilities let the official pipeline and dashboard work even before the
shared database clusters are available.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.core.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEGACY_STORAGE_DIR = PROJECT_ROOT / "backend" / "backend" / "storage"


def ensure_storage_dir() -> Path:
    path = PROJECT_ROOT / settings.storage_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def storage_file(filename: str) -> Path:
    return ensure_storage_dir() / filename


def _legacy_storage_file(filename: str) -> Path:
    return LEGACY_STORAGE_DIR / filename


def _maybe_migrate_legacy_file(filename: str) -> None:
    current_path = storage_file(filename)
    legacy_path = _legacy_storage_file(filename)

    if current_path.exists() and current_path.stat().st_size > 4:
        return

    if not legacy_path.exists() or legacy_path.stat().st_size <= 4:
        return

    current_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy_path, current_path)


def read_json_file(filename: str, default: Any) -> Any:
    _maybe_migrate_legacy_file(filename)
    path = storage_file(filename)
    if not path.exists():
        write_json_file(filename, default)
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_file(filename: str, data: Any) -> None:
    path = storage_file(filename)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, separators=(",", ":"))

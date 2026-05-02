"""
Hashing utilities for act integrity verification.
TODO: implement SHA-256 hash of act content for audit trail.
"""
from __future__ import annotations

import hashlib
import json


def hash_acta(data: dict) -> str:
    normalized = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    storage_dirs = [
        project_root / "backend" / "storage",
        project_root / "backend" / "backend" / "storage",
    ]

    for storage_dir in storage_dirs:
        storage_dir.mkdir(parents=True, exist_ok=True)
        for filename in ("oficial_actas.json", "auditoria_oficial.json"):
            path = storage_dir / filename
            path.write_text("[]\n", encoding="utf-8")
            print(f"Reset: {path}")


if __name__ == "__main__":
    main()

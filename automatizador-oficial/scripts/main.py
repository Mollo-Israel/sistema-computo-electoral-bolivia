from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from api_client import post_json
from csv_reader import load_rows


def _chunked(items: list[dict], chunk_size: int):
    for start in range(0, len(items), chunk_size):
        yield items[start:start + chunk_size]


def run(
    input_path: str,
    api_base: str,
    batch: bool,
    usuario_id: int | None,
    dry_run: bool,
    limit: int | None,
    chunk_size: int,
) -> None:
    rows = load_rows(input_path, default_usuario_id=usuario_id)
    if limit is not None:
        rows = rows[:limit]

    if dry_run:
        print(json.dumps({"preview": rows[:3], "total": len(rows)}, ensure_ascii=False, indent=2))
        return

    if batch:
        all_results = []
        started = time.perf_counter()
        for chunk_index, chunk in enumerate(_chunked(rows, chunk_size), start=1):
            chunk_started = time.perf_counter()
            payload = {"actas": chunk}
            response = post_json(f"{api_base.rstrip('/')}/api/oficial/importar-csv", payload)
            elapsed = round(time.perf_counter() - chunk_started, 2)
            chunk_result = {
                "chunk": chunk_index,
                "size": len(chunk),
                "status": response.get("status"),
                "message": response.get("message"),
                "summary": response.get("data"),
                "elapsed_seconds": elapsed,
            }
            all_results.append(chunk_result)
            print(
                json.dumps(
                    {
                        "progress": f"{min(chunk_index * chunk_size, len(rows))}/{len(rows)}",
                        "chunk": chunk_index,
                        "elapsed_seconds": elapsed,
                        "summary": response.get("data"),
                    },
                    ensure_ascii=False,
                )
            )

        print(
            json.dumps(
                {
                    "chunks": all_results,
                    "total": len(rows),
                    "total_elapsed_seconds": round(time.perf_counter() - started, 2),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    results = []
    started = time.perf_counter()
    for row_index, row in enumerate(rows, start=1):
        result = post_json(f"{api_base.rstrip('/')}/api/oficial/transcribir", row)
        results.append(result)
        if row_index % 100 == 0:
            print(
                json.dumps(
                    {
                        "progress": f"{row_index}/{len(rows)}",
                        "elapsed_seconds": round(time.perf_counter() - started, 2),
                    },
                    ensure_ascii=False,
                )
            )

    print(json.dumps({"total": len(results), "resultados": results}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatizador oficial para cargar actas CSV o Excel al backend.")
    parser.add_argument(
        "--archivo",
        default=str(Path("Recursos Practica 4.xlsx").resolve()),
        help="Ruta al archivo oficial (.csv, .xlsx, .xls).",
    )
    parser.add_argument("--api-base", default="http://127.0.0.1:8000", help="Base URL del backend.")
    parser.add_argument("--usuario-id", type=int, default=None, help="Usuario de respaldo para filas sin usuario.")
    parser.add_argument("--por-lote", action="store_true", help="Enviar todas las filas al endpoint batch.")
    parser.add_argument("--limite", type=int, default=None, help="Procesar solo las primeras N filas.")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Tamaño de bloque al usar --por-lote.")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar el mapeo del CSV.")
    args = parser.parse_args()

    run(
        args.archivo,
        args.api_base,
        args.por_lote,
        args.usuario_id,
        args.dry_run,
        args.limite,
        args.chunk_size,
    )


if __name__ == "__main__":
    main()

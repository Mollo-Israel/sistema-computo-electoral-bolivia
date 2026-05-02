"""
OCR pipeline orchestrator for RRV actas.
Responsible: MOLLO.

This module is the integration point between image extraction and the
RRV validator. It ONLY captures and structures OCR data — it does NOT
decide whether an acta is VALIDADA, RECHAZADA, or OBSERVADA.

Full single-file flow:
  PNG → field_extractor.extract_field_crops()
      → ocr_reader.ocr_field() per crop
      → merge pixel-analysis status + OCR status
      → compute votos_emitidos (always CALCULADO, never read from image)
      → add OCR flags
      → return structured result dict

Batch flow (1 000 actas):
  process_batch() distributes work across a ThreadPoolExecutor so
  CPU-bound Tesseract calls run in parallel while keeping the async
  interface for FastAPI handlers.

CLI:
  python backend/app/services/ocr/ocr_service.py \\
    --input samples/actas/converted --limit 5 \\
    --output samples/actas/ocr_results_debug.json

  python backend/app/services/ocr/ocr_service.py \\
    --input samples/actas/converted/acta_x_page1.png \\
    --output samples/actas/ocr_single_result.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.services.ocr.field_extractor import (
    PROJECT_ROOT,
    collect_image_files,
    extract_field_crops,
)
from app.services.ocr.ocr_reader import FieldOCRResult, ocr_field, parse_time
from app.services.ocr.pdf_converter import convert_pdf_to_images

# ── Paths ─────────────────────────────────────────────────────────────────────

DEFAULT_INPUT_DIR  = PROJECT_ROOT / "samples" / "actas" / "converted"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "samples" / "actas"

# ── Field classification ───────────────────────────────────────────────────────

# Fields that drive the arithmetic pre-checks and are flagged individually
_CRITICAL_NUM = {
    "mesa_codigo",
    "nro_mesa",
    "nro_votantes",
    "total_boletas",
    "partido_1_votos",
    "partido_2_votos",
    "partido_3_votos",
    "partido_4_votos",
    "votos_validos",
    "votos_blancos",
    "votos_nulos",
}
_IMPORTANT_NUM = {
    "boletas_no_utilizadas",
    "apertura_hora",
    "apertura_minutos",
    "cierre_hora",
    "cierre_minutos",
}
_TEXT_FIELDS = {
    "departamento",
    "provincia",
    "municipio",
    "recinto_nombre",
    "recinto_direccion",
    "observaciones",
}

# Internal fields that are redundant (combined time crops — used only as fallback)
_TIME_FALLBACK_FIELDS = {"apertura_time", "cierre_time"}

# ── Bolivian electoral code derivation ───────────────────────────────────────
#
# Code structure (13 digits): D PP MMM RRRR NNN
#   D(1) = departamento, PP(2) = provincia, MMM(3) = municipio,
#   RRRR(4) = recinto, NNN(3) = mesa
#
# Example: 1 01 020 0001 001
#   codigo_territorial = first 6 chars  → "101020" (dept+prov+mun)
#   codigo_recinto     = first 10 chars → "1010200001" (dept+prov+mun+recinto)

def _derive_codes(mesa_codigo: str) -> tuple[str, str]:
    code = re.sub(r"\D", "", mesa_codigo)   # keep only digits
    ct = code[:6]  if len(code) >= 6  else code
    cr = code[:10] if len(code) >= 10 else code
    return ct, cr


# ── Status merge ───────────────────────────────────────────────────────────────

def _merge_status(pixel_status: str, ocr_status: str) -> str:
    """
    Combine pixel-analysis status (from field_extractor) with OCR status.

    pixel_status values: OK | POSIBLE_OBSTRUCCION | POSIBLE_CAMPO_VACIO
                         POSIBLE_CAMPO_BORROSO_O_VACIO
    ocr_status values:   OK | BAJA_CONFIANZA | CAMPO_VACIO | OCR_ERROR

    Rule:
      - Strong obstruction → always POSIBLE_OBSTRUCCION (regardless of OCR)
      - Pre-detected empty + OCR also empty → CAMPO_VACIO
      - Pre-detected empty/blurry + OCR got something → BAJA_CONFIANZA
      - Otherwise → trust ocr_status
    """
    if pixel_status == "POSIBLE_OBSTRUCCION":
        if ocr_status == "OK":
            return "BAJA_CONFIANZA"
        return "POSIBLE_OBSTRUCCION"
    if pixel_status in ("POSIBLE_CAMPO_VACIO", "POSIBLE_CAMPO_BORROSO_O_VACIO"):
        if ocr_status == "CAMPO_VACIO":
            return "CAMPO_VACIO"
        if ocr_status == "OK":
            return "BAJA_CONFIANZA"
    return ocr_status


# ── Value helpers ─────────────────────────────────────────────────────────────

def _to_int(ocr_results: dict[str, FieldOCRResult], name: str) -> int | None:
    r = ocr_results.get(name)
    if not r or not r.value:
        return None
    try:
        return int(r.value)
    except (ValueError, TypeError):
        return None


def _to_str(ocr_results: dict[str, FieldOCRResult], name: str) -> str | None:
    r = ocr_results.get(name)
    return r.value if r and r.value else None


# ── Core builder ──────────────────────────────────────────────────────────────

def _build_ocr_result(extraction: dict) -> dict[str, Any]:
    """
    Given the output of extract_field_crops(), OCR every field crop and
    assemble the structured OCR result dict.

    votos_emitidos is always computed (never read from the image).
    Text fields do not block the pipeline when their OCR is poor.
    """
    crops      = extraction["fields"]          # dict[name, np.ndarray]
    field_meta = {m.name: m for m in extraction["metadata"]}

    # ── OCR every crop ──────────────────────────────────────────────
    ocr_results: dict[str, FieldOCRResult] = {}
    for name, crop in crops.items():
        meta = field_meta[name]
        ocr_results[name] = ocr_field(
            crop,
            meta.field_type,
            meta.expected_digits,
        )

    # ── Merge pixel + OCR statuses ──────────────────────────────────
    campo_status:    dict[str, str]   = {}
    campo_confianza: dict[str, float] = {}
    campo_estrategia: dict[str, str]  = {}

    for name, ocr_res in ocr_results.items():
        if name in _TIME_FALLBACK_FIELDS:
            continue   # exclude combined time crops from public maps
        meta = field_meta[name]
        campo_status[name]     = _merge_status(meta.status, ocr_res.status)
        campo_confianza[name]  = ocr_res.confidence
        campo_estrategia[name] = ocr_res.strategy

    # ── Numeric fields ───────────────────────────────────────────────
    nro_mesa     = _to_int(ocr_results, "nro_mesa")
    nro_votantes = _to_int(ocr_results, "nro_votantes")
    total_boletas         = _to_int(ocr_results, "total_boletas")
    boletas_no_utilizadas = _to_int(ocr_results, "boletas_no_utilizadas")

    p1 = _to_int(ocr_results, "partido_1_votos")
    p2 = _to_int(ocr_results, "partido_2_votos")
    p3 = _to_int(ocr_results, "partido_3_votos")
    p4 = _to_int(ocr_results, "partido_4_votos")

    votos_validos = _to_int(ocr_results, "votos_validos")
    votos_blancos = _to_int(ocr_results, "votos_blancos")
    votos_nulos   = _to_int(ocr_results, "votos_nulos")

    # votos_emitidos: always computed — never read from image
    votos_emitidos         = None
    votos_emitidos_origen  = "CALCULADO"
    if None not in (votos_validos, votos_blancos, votos_nulos):
        votos_emitidos = votos_validos + votos_blancos + votos_nulos

    # ── Time fields: individual crops primary, combined as fallback ──
    apertura_hora     = _to_int(ocr_results, "apertura_hora")
    apertura_minutos  = _to_int(ocr_results, "apertura_minutos")
    if apertura_hora is None or apertura_minutos is None:
        combined = _to_str(ocr_results, "apertura_time") or ""
        fh, fm = parse_time(combined)
        if apertura_hora is None:
            apertura_hora = fh
        if apertura_minutos is None:
            apertura_minutos = fm

    cierre_hora    = _to_int(ocr_results, "cierre_hora")
    cierre_minutos = _to_int(ocr_results, "cierre_minutos")
    if cierre_hora is None or cierre_minutos is None:
        combined = _to_str(ocr_results, "cierre_time") or ""
        fh, fm = parse_time(combined)
        if cierre_hora is None:
            cierre_hora = fh
        if cierre_minutos is None:
            cierre_minutos = fm

    # ── Identification ───────────────────────────────────────────────
    mesa_codigo_raw = _to_str(ocr_results, "mesa_codigo") or ""
    ct, cr = _derive_codes(mesa_codigo_raw) if mesa_codigo_raw else ("", "")

    # ── Text fields (best-effort, never block pipeline) ──────────────
    departamento     = _to_str(ocr_results, "departamento")
    provincia        = _to_str(ocr_results, "provincia")
    municipio        = _to_str(ocr_results, "municipio")
    recinto_nombre   = _to_str(ocr_results, "recinto_nombre")
    recinto_direccion = _to_str(ocr_results, "recinto_direccion")
    observaciones    = _to_str(ocr_results, "observaciones")

    # ── OCR flags (technical, not legal) ────────────────────────────
    flags: list[str] = []

    orientation = extraction["orientation_status"]
    if orientation == "CORREGIDA":
        flags.append("ORIENTACION_CORREGIDA")
    elif orientation == "ORIENTACION_INCIERTA":
        flags.append("ORIENTACION_INCIERTA")

    if abs(extraction.get("skew_angle", 0.0)) > 1.0:
        flags.append(f"SKEW_CORREGIDO:{extraction['skew_angle']}deg")

    # Per-field flags — only for critical and important numeric fields
    for fname in (*_CRITICAL_NUM, *_IMPORTANT_NUM):
        status = campo_status.get(fname)
        if status == "POSIBLE_OBSTRUCCION":
            flags.append(f"POSIBLE_OBSTRUCCION:{fname}")
        elif status == "CAMPO_VACIO":
            flags.append(f"CAMPO_VACIO:{fname}")
        elif status == "BAJA_CONFIANZA":
            flags.append(f"BAJA_CONFIANZA:{fname}")
        elif status == "OCR_ERROR":
            flags.append(f"OCR_ERROR:{fname}")

    # Arithmetic pre-check (not a legal decision — informs the validator)
    if None not in (p1, p2, p3, p4, votos_validos):
        if (p1 + p2 + p3 + p4) != votos_validos:
            flags.append("SUMA_PARTIDOS_NO_COINCIDE_PRECHECK")

    # ── Assemble final result ────────────────────────────────────────
    return {
        "source_image":        extraction["source_image"],

        # CAMPOS_ESTANDAR
        "mesa_codigo":          mesa_codigo_raw or None,
        "codigo_territorial":   ct or None,
        "codigo_recinto":       cr or None,
        "nro_mesa":             nro_mesa,
        "departamento":         departamento,
        "provincia":            provincia,
        "municipio":            municipio,
        "recinto_nombre":       recinto_nombre,
        "recinto_direccion":    recinto_direccion,
        "nro_votantes":         nro_votantes,
        "total_boletas":        total_boletas,
        "boletas_no_utilizadas": boletas_no_utilizadas,
        "partido_1_votos":      p1,
        "partido_2_votos":      p2,
        "partido_3_votos":      p3,
        "partido_4_votos":      p4,
        "votos_validos":        votos_validos,
        "votos_blancos":        votos_blancos,
        "votos_nulos":          votos_nulos,
        "votos_emitidos":       votos_emitidos,
        "votos_emitidos_origen": votos_emitidos_origen,

        # Extra metadata fields
        "apertura_hora":        apertura_hora,
        "apertura_minutos":     apertura_minutos,
        "cierre_hora":          cierre_hora,
        "cierre_minutos":       cierre_minutos,
        "observaciones":        observaciones,

        # OCR quality maps
        "campo_confianza":  campo_confianza,
        "campo_status":     campo_status,
        "campo_estrategia": campo_estrategia,
        "flags_ocr":        flags,

        # Imaging metadata for traceability
        "metadata_captura": {
            "rotation_applied":       extraction["rotation_applied"],
            "orientation_status":     extraction["orientation_status"],
            "skew_angle":             extraction.get("skew_angle", 0.0),
            "external_margin_cropped": extraction["external_margin_cropped"],
            "normalization_mode":     extraction["normalization_mode"],
        },
    }


def _error_result(source_file: str, exc: Exception) -> dict[str, Any]:
    return {
        "source_image":        source_file,
        "mesa_codigo":          None,
        "codigo_territorial":   None,
        "codigo_recinto":       None,
        "nro_mesa":             None,
        "departamento":         None,
        "provincia":            None,
        "municipio":            None,
        "recinto_nombre":       None,
        "recinto_direccion":    None,
        "nro_votantes":         None,
        "total_boletas":        None,
        "boletas_no_utilizadas": None,
        "partido_1_votos":      None,
        "partido_2_votos":      None,
        "partido_3_votos":      None,
        "partido_4_votos":      None,
        "votos_validos":        None,
        "votos_blancos":        None,
        "votos_nulos":          None,
        "votos_emitidos":       None,
        "votos_emitidos_origen": "CALCULADO",
        "apertura_hora":        None,
        "apertura_minutos":     None,
        "cierre_hora":          None,
        "cierre_minutos":       None,
        "observaciones":        None,
        "campo_confianza":      {},
        "campo_status":         {},
        "campo_estrategia":     {},
        "flags_ocr":            [f"OCR_ERROR: {exc}"],
        "metadata_captura":     {},
    }


# ── Synchronous workers (run in ThreadPoolExecutor) ───────────────────────────

def _process_image_sync(
    image_path: Path,
    debug: bool = False,
) -> dict[str, Any]:
    extraction = extract_field_crops(image_path, debug=debug)
    return _build_ocr_result(extraction)


def _process_pdf_sync(
    pdf_path: Path,
    debug: bool = False,
) -> dict[str, Any]:
    pages = convert_pdf_to_images(pdf_path)
    if not pages:
        raise ValueError(f"No se pudo convertir el PDF: {pdf_path}")
    # Each RRV acta is a single page; use page 1
    return _process_image_sync(Path(pages[0].output_path), debug=debug)


def _worker(path: Path, debug: bool) -> dict[str, Any]:
    try:
        if path.suffix.lower() == ".pdf":
            return _process_pdf_sync(path, debug)
        return _process_image_sync(path, debug)
    except Exception as exc:
        return _error_result(str(path), exc)


# ── Public async API ──────────────────────────────────────────────────────────

async def process_image(
    image_path: str,
    debug: bool = False,
) -> dict[str, Any]:
    """Process a single PNG/JPG image asynchronously."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            None, _process_image_sync, Path(image_path), debug,
        )
    except Exception as exc:
        return _error_result(image_path, exc)


async def process_pdf(
    pdf_path: str,
    debug: bool = False,
) -> dict[str, Any]:
    """Convert a PDF to image then run the full OCR pipeline."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            None, _process_pdf_sync, Path(pdf_path), debug,
        )
    except Exception as exc:
        return _error_result(pdf_path, exc)


async def process_batch(
    file_paths: list[str | Path],
    max_workers: int = 2,
    debug: bool = False,
) -> list[dict[str, Any]]:
    """
    Process a batch of PDF or image files in parallel.

    Uses ThreadPoolExecutor (max_workers=2 default — conservative for most
    development environments) so Tesseract runs concurrently without
    blocking the event loop.

    Errors in individual files are isolated: each failure returns a result
    dict with flags_ocr=["OCR_ERROR: ..."] rather than raising.

    Args:
        file_paths:  list of .pdf, .png, .jpg, or .jpeg paths.
        max_workers: parallel Tesseract workers. Raise to 4–8 on CI/server.
        debug:       save field crops and manifests to fields_debug/ when True.
    """
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            loop.run_in_executor(pool, _worker, Path(p), debug)
            for p in file_paths
        ]
        results = await asyncio.gather(*futures)
    return list(results)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _collect_input(input_path: Path, limit: int | None) -> list[Path]:
    """Accept image files OR PDFs; single file or directory."""
    supported_images = {".png", ".jpg", ".jpeg"}
    supported_all    = supported_images | {".pdf"}

    input_path = input_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"No existe: {input_path}")

    if input_path.is_file():
        if input_path.suffix.lower() not in supported_all:
            raise ValueError(f"Formato no soportado: {input_path.suffix}")
        return [input_path]

    files = sorted(
        p for p in input_path.iterdir()
        if p.is_file() and p.suffix.lower() in supported_all
    )
    return files[:limit] if limit is not None else files


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OCR de actas electorales RRV — produce JSON estructurado por acta."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Carpeta con imágenes PNG/JPG o PDF, o ruta a un solo archivo.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta JSON de salida. Omitir para mostrar en consola.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Procesar solo las primeras N actas.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Número de workers Tesseract en paralelo (default 2).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Guardar recortes de campos y manifests en fields_debug/.",
    )
    return parser.parse_args()


def _print_summary(results: list[dict]) -> None:
    print(f"\n{'─'*60}")
    print(f"  Actas procesadas: {len(results)}")
    ok    = sum(1 for r in results if not r["flags_ocr"])
    flags = sum(1 for r in results if r["flags_ocr"])
    print(f"  Sin flags OCR:    {ok}")
    print(f"  Con flags OCR:    {flags}")
    print(f"{'─'*60}")
    for r in results:
        name  = Path(r["source_image"]).name
        mesa  = r.get("mesa_codigo") or "?"
        conf_vals = list(r["campo_confianza"].values())
        avg_conf  = round(sum(conf_vals) / len(conf_vals), 2) if conf_vals else 0.0
        n_flags   = len(r["flags_ocr"])
        print(f"  {name:<40} mesa={mesa:<14} conf≈{avg_conf:.2f}  flags={n_flags}")


def main() -> None:
    args = _parse_args()

    try:
        files = _collect_input(args.input, args.limit)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

    if not files:
        print("No se encontraron archivos para procesar.")
        raise SystemExit(0)

    print(f"Procesando {len(files)} acta(s) con {args.workers} worker(s)...")

    results = asyncio.run(
        process_batch(
            [str(f) for f in files],
            max_workers=args.workers,
            debug=args.debug,
        )
    )

    _print_summary(results)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nResultados guardados en: {args.output.resolve()}")
    else:
        print("\n" + json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

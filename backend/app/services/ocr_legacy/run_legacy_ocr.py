from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pytesseract

from app.services.ocr_legacy.ocr_service import OCRService


def configure_tesseract() -> None:
    tesseract_cmd = os.getenv(
        "TESSERACT_CMD",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    )

    if Path(tesseract_cmd).exists():
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def result_to_dict(result) -> dict:
    acta_rrv = result.to_acta_rrv_dict()

    return {
        "extractor": "ocr_legacy_global_tesseract",
        "metricas": result.to_metricas_dict(),
        "campos_extraidos": result.campos,
        "acta_rrv": acta_rrv,
        "texto_crudo": result.texto_crudo,
        "errores_procesamiento": result.errores_procesamiento,
    }


def process_file(input_path: Path) -> dict:
    service = OCRService()
    content = input_path.read_bytes()

    if input_path.suffix.lower() == ".pdf":
        result = service.process_pdf_with_filename(content, input_path.name)
    else:
        result = service.process_image(content, input_path.name)

    return result_to_dict(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    configure_tesseract()

    input_path = Path(args.input).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {input_path}")

    result = process_file(input_path)

    text = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")

    print(text)


if __name__ == "__main__":
    main()
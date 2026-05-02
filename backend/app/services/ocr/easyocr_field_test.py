from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import cv2
import easyocr


NUMERIC_FIELDS = {
    "mesa_codigo",
    "nro_mesa",
    "nro_votantes",
    "total_boletas",
    "boletas_no_utilizadas",
    "partido_1_votos",
    "partido_2_votos",
    "partido_3_votos",
    "partido_4_votos",
    "votos_validos",
    "votos_blancos",
    "votos_nulos",
    "apertura_hora",
    "apertura_minutos",
    "cierre_hora",
    "cierre_minutos",
}

TEXT_FIELDS = {
    "departamento",
    "provincia",
    "municipio",
    "recinto_nombre",
    "recinto_direccion",
    "observaciones",
}

FIELDS_TO_TEST = [
    "mesa_codigo",
    "nro_mesa",
    "departamento",
    "provincia",
    "municipio",
    "recinto_nombre",
    "recinto_direccion",
    "nro_votantes",
    "total_boletas",
    "boletas_no_utilizadas",
    "partido_1_votos",
    "partido_2_votos",
    "partido_3_votos",
    "partido_4_votos",
    "votos_validos",
    "votos_blancos",
    "votos_nulos",
    "apertura_hora",
    "apertura_minutos",
    "cierre_hora",
    "cierre_minutos",
    "observaciones",
]


def clean_digits(text: str) -> str | None:
    digits = re.sub(r"\D", "", text)
    return digits or None


def clean_text(text: str) -> str | None:
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def read_image(path: Path):
    image = cv2.imread(str(path))

    if image is None:
        raise FileNotFoundError(f"No se pudo leer la imagen: {path}")

    return image


def run_easyocr_on_field(reader: easyocr.Reader, image_path: Path, field_name: str) -> dict:
    image = read_image(image_path)

    allowlist = "0123456789" if field_name in NUMERIC_FIELDS else None

    results = reader.readtext(
        image,
        detail=1,
        paragraph=False,
        decoder="greedy",
        allowlist=allowlist,
    )

    raw_parts = []
    confidences = []

    for item in results:
        text = str(item[1]).strip()
        conf = float(item[2])

        if text:
            raw_parts.append(text)
            confidences.append(conf)

    raw_text = " ".join(raw_parts).strip()
    confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

    if field_name in NUMERIC_FIELDS:
        value = clean_digits(raw_text)
    else:
        value = clean_text(raw_text)

    return {
        "field": field_name,
        "value": value,
        "raw_text": raw_text,
        "confidence": confidence,
        "source": str(image_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fields-dir", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    fields_dir = Path(args.fields_dir).resolve()

    if not fields_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta: {fields_dir}")

    reader = easyocr.Reader(["es", "en"], gpu=False)

    output = {}

    for field_name in FIELDS_TO_TEST:
        image_path = fields_dir / f"{field_name}.png"

        if not image_path.exists():
            output[field_name] = {
                "value": None,
                "raw_text": "",
                "confidence": 0.0,
                "error": "NO_EXISTE_RECORTE",
            }
            continue

        output[field_name] = run_easyocr_on_field(reader, image_path, field_name)

    text = json.dumps(output, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
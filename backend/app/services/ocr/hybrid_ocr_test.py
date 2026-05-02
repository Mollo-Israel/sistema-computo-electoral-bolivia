from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import cv2
import easyocr

from app.services.ocr.ocr_reader import ocr_field


FIELD_SPECS = {
    "mesa_codigo": {"type": "printed_number", "digits": 13},
    "nro_mesa": {"type": "printed_number", "digits": 1},
    "nro_votantes": {"type": "printed_number", "digits": 3},
    "total_boletas": {"type": "handwritten_number", "digits": 3},
    "boletas_no_utilizadas": {"type": "handwritten_number", "digits": 3},
    "partido_1_votos": {"type": "handwritten_number", "digits": 3},
    "partido_2_votos": {"type": "handwritten_number", "digits": 3},
    "partido_3_votos": {"type": "handwritten_number", "digits": 3},
    "partido_4_votos": {"type": "handwritten_number", "digits": 3},
    "votos_validos": {"type": "handwritten_number", "digits": 3},
    "votos_blancos": {"type": "handwritten_number", "digits": 3},
    "votos_nulos": {"type": "handwritten_number", "digits": 3},
    "apertura_hora": {"type": "handwritten_number", "digits": 2},
    "apertura_minutos": {"type": "handwritten_number", "digits": 2},
    "cierre_hora": {"type": "handwritten_number", "digits": 2},
    "cierre_minutos": {"type": "handwritten_number", "digits": 2},
    "departamento": {"type": "printed_text", "digits": None},
    "provincia": {"type": "printed_text", "digits": None},
    "municipio": {"type": "printed_text", "digits": None},
    "recinto_nombre": {"type": "printed_text", "digits": None},
    "recinto_direccion": {"type": "printed_text", "digits": None},
    "observaciones": {"type": "printed_text", "digits": None},
}


def clean_digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def clean_text(text: str) -> str | None:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text or None


def read_image(path: Path):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"No se pudo leer la imagen: {path}")
    return img


def easyocr_read(reader: easyocr.Reader, image, numeric: bool) -> tuple[str | None, str, float]:
    allowlist = "0123456789" if numeric else None

    results = reader.readtext(
        image,
        detail=1,
        paragraph=False,
        decoder="greedy",
        allowlist=allowlist,
    )

    raw_parts = []
    confs = []

    for item in results:
        text = str(item[1]).strip()
        conf = float(item[2])

        if text:
            raw_parts.append(text)
            confs.append(conf)

    raw = " ".join(raw_parts).strip()
    confidence = round(sum(confs) / len(confs), 3) if confs else 0.0

    if numeric:
        value = clean_digits(raw) or None
    else:
        value = clean_text(raw)

    return value, raw, confidence


def tesseract_read(image, field_type: str, expected_digits: int | None) -> tuple[str | None, str, float, str]:
    result = ocr_field(image, field_type, expected_digits)
    return result.value, result.raw_text, result.confidence, result.strategy


def choose_digit(
    tess_value: str | None,
    tess_conf: float,
    easy_value: str | None,
    easy_conf: float,
) -> tuple[str | None, str, float]:
    t_digit = clean_digits(tess_value or "")
    e_digit = clean_digits(easy_value or "")

    t_digit = t_digit[0] if t_digit else None
    e_digit = e_digit[0] if e_digit else None

    if t_digit and e_digit and t_digit == e_digit:
        return t_digit, "agree", round(max(tess_conf, easy_conf), 3)

    if e_digit and easy_conf >= 0.80:
        return e_digit, "easyocr", easy_conf

    if t_digit and tess_conf >= 0.55:
        return t_digit, "tesseract", tess_conf

    if e_digit and easy_conf >= tess_conf:
        return e_digit, "easyocr_low", easy_conf

    if t_digit:
        return t_digit, "tesseract_low", tess_conf

    return None, "empty", 0.0


def read_numeric_from_digit_folder(
    reader: easyocr.Reader,
    fields_dir: Path,
    field_name: str,
    field_type: str,
    expected_digits: int,
) -> dict | None:
    digit_dir = fields_dir / "digits" / field_name

    if not digit_dir.exists():
        return None

    digit_paths = sorted(digit_dir.glob("*.png"))

    if len(digit_paths) != expected_digits:
        return None

    digits = []
    details = []

    for path in digit_paths:
        image = read_image(path)

        tess_value, tess_raw, tess_conf, tess_strategy = tesseract_read(
            image,
            field_type,
            1,
        )

        easy_value, easy_raw, easy_conf = easyocr_read(
            reader,
            image,
            numeric=True,
        )

        chosen, source, chosen_conf = choose_digit(
            tess_value,
            tess_conf,
            easy_value,
            easy_conf,
        )

        details.append(
            {
                "digit_file": str(path),
                "tesseract_value": tess_value,
                "tesseract_raw": tess_raw,
                "tesseract_confidence": tess_conf,
                "tesseract_strategy": tess_strategy,
                "easyocr_value": easy_value,
                "easyocr_raw": easy_raw,
                "easyocr_confidence": easy_conf,
                "chosen": chosen,
                "chosen_source": source,
                "chosen_confidence": chosen_conf,
            }
        )

        if chosen is None:
            return {
                "value": None,
                "raw_text": "",
                "confidence": 0.0,
                "status": "CAMPO_VACIO",
                "strategy": "digit_folder_failed",
                "details": details,
            }

        digits.append(chosen)

    value = "".join(digits)
    confidence = round(
        sum(item["chosen_confidence"] for item in details) / len(details),
        3,
    )

    status = "OK" if confidence >= 0.60 else "BAJA_CONFIANZA"

    return {
        "value": value,
        "raw_text": " ".join(digits),
        "confidence": confidence,
        "status": status,
        "strategy": "digit_folder_hybrid",
        "details": details,
    }


def read_numeric_fallback(
    reader: easyocr.Reader,
    fields_dir: Path,
    field_name: str,
    field_type: str,
    expected_digits: int,
) -> dict:
    image_path = fields_dir / f"{field_name}.png"

    if not image_path.exists():
        return {
            "value": None,
            "raw_text": "",
            "confidence": 0.0,
            "status": "NO_EXISTE_RECORTE",
            "strategy": "missing_field_crop",
        }

    image = read_image(image_path)

    tess_value, tess_raw, tess_conf, tess_strategy = tesseract_read(
        image,
        field_type,
        expected_digits,
    )

    easy_value, easy_raw, easy_conf = easyocr_read(
        reader,
        image,
        numeric=True,
    )

    candidates = []

    if tess_value:
        tess_digits = clean_digits(tess_value)
        if len(tess_digits) == expected_digits:
            candidates.append(
                {
                    "value": tess_digits,
                    "raw_text": tess_raw,
                    "confidence": tess_conf,
                    "engine": "tesseract",
                    "strategy": tess_strategy,
                }
            )

    if easy_value:
        easy_digits = clean_digits(easy_value)
        if len(easy_digits) == expected_digits:
            candidates.append(
                {
                    "value": easy_digits,
                    "raw_text": easy_raw,
                    "confidence": easy_conf,
                    "engine": "easyocr",
                    "strategy": "easyocr_full_crop",
                }
            )

        if len(easy_digits) == expected_digits - 1:
            candidates.append(
                {
                    "value": easy_digits.zfill(expected_digits),
                    "raw_text": easy_raw,
                    "confidence": max(0.0, easy_conf - 0.10),
                    "engine": "easyocr_zfill",
                    "strategy": "easyocr_full_crop_zfill",
                }
            )

    if candidates:
        best = max(candidates, key=lambda item: item["confidence"])
        return {
            "value": best["value"],
            "raw_text": best["raw_text"],
            "confidence": round(best["confidence"], 3),
            "status": "OK" if best["confidence"] >= 0.60 else "BAJA_CONFIANZA",
            "strategy": best["strategy"],
            "engine": best["engine"],
            "tesseract": {
                "value": tess_value,
                "raw": tess_raw,
                "confidence": tess_conf,
                "strategy": tess_strategy,
            },
            "easyocr": {
                "value": easy_value,
                "raw": easy_raw,
                "confidence": easy_conf,
            },
        }

    return {
        "value": None,
        "raw_text": "",
        "confidence": 0.0,
        "status": "RECHAZADO_FORMATO",
        "strategy": "no_candidate_with_expected_length",
        "tesseract": {
            "value": tess_value,
            "raw": tess_raw,
            "confidence": tess_conf,
            "strategy": tess_strategy,
        },
        "easyocr": {
            "value": easy_value,
            "raw": easy_raw,
            "confidence": easy_conf,
        },
    }


def read_text_field(reader: easyocr.Reader, fields_dir: Path, field_name: str) -> dict:
    image_path = fields_dir / f"{field_name}.png"

    if not image_path.exists():
        return {
            "value": None,
            "raw_text": "",
            "confidence": 0.0,
            "status": "NO_EXISTE_RECORTE",
            "strategy": "missing_field_crop",
        }

    image = read_image(image_path)

    tess_value, tess_raw, tess_conf, tess_strategy = tesseract_read(
        image,
        "printed_text",
        None,
    )

    easy_value, easy_raw, easy_conf = easyocr_read(
        reader,
        image,
        numeric=False,
    )

    if easy_value and easy_conf >= tess_conf:
        return {
            "value": easy_value,
            "raw_text": easy_raw,
            "confidence": easy_conf,
            "status": "OK" if easy_conf >= 0.60 else "BAJA_CONFIANZA",
            "strategy": "easyocr_text",
            "tesseract": {
                "value": tess_value,
                "raw": tess_raw,
                "confidence": tess_conf,
                "strategy": tess_strategy,
            },
        }

    return {
        "value": tess_value,
        "raw_text": tess_raw,
        "confidence": tess_conf,
        "status": "OK" if tess_conf >= 0.60 else "BAJA_CONFIANZA",
        "strategy": tess_strategy,
        "easyocr": {
            "value": easy_value,
            "raw": easy_raw,
            "confidence": easy_conf,
        },
    }


def normalize_output(results: dict) -> dict:
    output = {}

    for field_name, result in results.items():
        value = result.get("value")

        if field_name in FIELD_SPECS and FIELD_SPECS[field_name]["digits"] is not None:
            if value is None:
                output[field_name] = None
            else:
                try:
                    output[field_name] = int(value)
                except ValueError:
                    output[field_name] = None
        else:
            output[field_name] = value

    mesa_codigo = results.get("mesa_codigo", {}).get("value")

    if mesa_codigo and len(mesa_codigo) >= 10:
        output["codigo_territorial"] = mesa_codigo[:6]
        output["codigo_recinto"] = mesa_codigo[:10]
    else:
        output["codigo_territorial"] = None
        output["codigo_recinto"] = None

    validos = output.get("votos_validos")
    blancos = output.get("votos_blancos")
    nulos = output.get("votos_nulos")

    if validos is not None and blancos is not None and nulos is not None:
        output["votos_emitidos"] = validos + blancos + nulos
        output["votos_emitidos_origen"] = "CALCULADO"
    else:
        output["votos_emitidos"] = None
        output["votos_emitidos_origen"] = "NO_CALCULADO"

    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fields-dir", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--details-output", default=None)
    args = parser.parse_args()

    fields_dir = Path(args.fields_dir).resolve()

    if not fields_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta: {fields_dir}")

    reader = easyocr.Reader(["es", "en"], gpu=False)

    detailed_results = {}

    for field_name, spec in FIELD_SPECS.items():
        field_type = spec["type"]
        expected_digits = spec["digits"]

        if expected_digits is None:
            detailed_results[field_name] = read_text_field(
                reader,
                fields_dir,
                field_name,
            )
            continue

        digit_result = read_numeric_from_digit_folder(
            reader,
            fields_dir,
            field_name,
            field_type,
            expected_digits,
        )

        if digit_result is not None and digit_result.get("value") is not None:
            detailed_results[field_name] = digit_result
        else:
            detailed_results[field_name] = read_numeric_fallback(
                reader,
                fields_dir,
                field_name,
                field_type,
                expected_digits,
            )

    final_output = normalize_output(detailed_results)

    if args.details_output:
        Path(args.details_output).write_text(
            json.dumps(detailed_results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    text = json.dumps(final_output, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
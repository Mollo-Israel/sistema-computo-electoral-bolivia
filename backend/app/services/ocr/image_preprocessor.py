from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "samples" / "actas" / "converted"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "samples" / "actas" / "processed"

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


@dataclass(frozen=True)
class ProcessedImage:
    source_image: str
    output_path: str
    width: int
    height: int
    skipped: bool = False


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_output_name(image_path: Path) -> str:
    return f"{image_path.stem}_processed.png"


def load_image(image_path: Path) -> np.ndarray:
    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")

    return image


def deskew(image: np.ndarray, max_angle: float = 8.0) -> tuple[np.ndarray, float]:
    """
    Correct small scan rotation using the minimum bounding rectangle of foreground pixels.
    Handles mobile-photo skew (1–8°). Returns (corrected_image, angle_applied_degrees).
    No-ops if the detected angle exceeds max_angle (likely a detection error).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 200:
        return image, 0.0

    angle = cv2.minAreaRect(coords)[2]
    # minAreaRect returns angles in [-90, 0); convert to [-45, 45)
    if angle < -45:
        angle = 90.0 + angle

    if abs(angle) > max_angle:
        return image, 0.0

    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    corrected = cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return corrected, round(angle, 2)


def preprocess_image(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)

    blurred = cv2.GaussianBlur(contrast, (3, 3), 0)

    binary = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )

    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return cleaned


def process_single_image(
    image_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    overwrite: bool = False,
) -> ProcessedImage:
    image_path = image_path.resolve()
    output_dir = output_dir.resolve()

    if not image_path.exists():
        raise FileNotFoundError(f"No existe la imagen: {image_path}")

    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato no soportado: {image_path}")

    ensure_directory(output_dir)

    output_path = output_dir / build_output_name(image_path)

    if output_path.exists() and not overwrite:
        return ProcessedImage(
            source_image=str(image_path),
            output_path=str(output_path),
            width=0,
            height=0,
            skipped=True,
        )

    image = load_image(image_path)
    processed = preprocess_image(image)

    success = cv2.imwrite(str(output_path), processed)

    if not success:
        raise RuntimeError(f"No se pudo guardar la imagen procesada: {output_path}")

    height, width = processed.shape[:2]

    return ProcessedImage(
        source_image=str(image_path),
        output_path=str(output_path),
        width=width,
        height=height,
        skipped=False,
    )


def process_image_directory(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    overwrite: bool = False,
) -> list[ProcessedImage]:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de entrada: {input_dir}")

    ensure_directory(output_dir)

    image_files = sorted(
        path for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    processed_images: list[ProcessedImage] = []

    for image_path in image_files:
        try:
            processed_images.append(
                process_single_image(
                    image_path=image_path,
                    output_dir=output_dir,
                    overwrite=overwrite,
                )
            )
        except Exception as error:
            print(f"Error procesando {image_path.name}: {error}")

    return processed_images


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocesa imágenes de actas para mejorar la lectura OCR."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Carpeta donde están las imágenes convertidas desde PDF.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Carpeta donde se guardarán las imágenes preprocesadas.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe imágenes ya preprocesadas.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    results = process_image_directory(
        input_dir=args.input,
        output_dir=args.output,
        overwrite=args.overwrite,
    )

    processed = sum(1 for item in results if not item.skipped)
    skipped = sum(1 for item in results if item.skipped)

    print(f"Imágenes procesadas: {processed}")
    print(f"Imágenes omitidas por existir: {skipped}")
    print(f"Salida: {args.output.resolve()}")


if __name__ == "__main__":
    main()
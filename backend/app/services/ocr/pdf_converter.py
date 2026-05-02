from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import fitz


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "samples" / "actas" / "raw"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "samples" / "actas" / "converted"


@dataclass(frozen=True)
class ConvertedPage:
    source_pdf: str
    page_number: int
    output_path: str
    width: int
    height: int
    skipped: bool = False


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_output_name(pdf_path: Path, page_number: int) -> str:
    return f"{pdf_path.stem}_page{page_number}.png"


def convert_pdf_to_images(
    pdf_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    dpi: int = 250,
    overwrite: bool = False,
) -> list[ConvertedPage]:
    pdf_path = pdf_path.resolve()
    output_dir = output_dir.resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"No existe el PDF: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"El archivo no es PDF: {pdf_path}")

    ensure_directory(output_dir)

    converted_pages: list[ConvertedPage] = []

    with fitz.open(pdf_path) as document:
        for index, page in enumerate(document, start=1):
            output_path = output_dir / build_output_name(pdf_path, index)

            if output_path.exists() and not overwrite:
                converted_pages.append(
                    ConvertedPage(
                        source_pdf=str(pdf_path),
                        page_number=index,
                        output_path=str(output_path),
                        width=0,
                        height=0,
                        skipped=True,
                    )
                )
                continue

            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            pixmap.save(output_path)

            converted_pages.append(
                ConvertedPage(
                    source_pdf=str(pdf_path),
                    page_number=index,
                    output_path=str(output_path),
                    width=pixmap.width,
                    height=pixmap.height,
                    skipped=False,
                )
            )

    return converted_pages


def convert_pdf_directory(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    dpi: int = 250,
    overwrite: bool = False,
) -> list[ConvertedPage]:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de entrada: {input_dir}")

    ensure_directory(output_dir)

    pdf_files = sorted(input_dir.glob("*.pdf"))
    converted_pages: list[ConvertedPage] = []

    for pdf_path in pdf_files:
        converted_pages.extend(
            convert_pdf_to_images(
                pdf_path=pdf_path,
                output_dir=output_dir,
                dpi=dpi,
                overwrite=overwrite,
            )
        )

    return converted_pages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convierte actas electorales en PDF a imágenes PNG para el flujo OCR RRV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Carpeta donde están los PDF originales.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Carpeta donde se guardarán las imágenes convertidas.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=250,
        help="Resolución de conversión. Recomendado: 200 a 300.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe imágenes ya convertidas.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    results = convert_pdf_directory(
        input_dir=args.input,
        output_dir=args.output,
        dpi=args.dpi,
        overwrite=args.overwrite,
    )

    generated = sum(1 for item in results if not item.skipped)
    skipped = sum(1 for item in results if item.skipped)

    print(f"Imágenes generadas: {generated}")
    print(f"Imágenes omitidas por existir: {skipped}")
    print(f"Salida: {args.output.resolve()}")


if __name__ == "__main__":
    main()
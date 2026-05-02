"""
Servicio principal OCR para actas electorales bolivianas.

Pipeline completo:
  1. Recibe bytes de PDF o imagen (JPG / PNG / TIFF / BMP)
  2. Convierte PDF → imágenes PIL  (pdf2image + poppler)
  3. Preprocesa cada imagen        (ImagePreprocessor)
  4. Ejecuta Tesseract OCR         (pytesseract, idioma español)
  5. Extrae campos del formulario  (FormParser)
  6. Calcula confianza combinada   (60 % OCR + 40 % campos extraídos)
  7. Retorna ActaOCRResult listo para el validador RRV

Confianza combinada ≥ 0.75  →  el validador lo acepta como VALIDADA
Confianza combinada  < 0.75  →  el validador lo marca OBSERVADA (OCR_BAJA_CONFIANZA)
Calidad imagen = MALA        →  el validador lo marca OBSERVADA (IMAGEN_ILEGIBLE)
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from PIL import Image

from .image_preprocessor import ImagePreprocessor
from .form_parser import FormParser

logger = logging.getLogger(__name__)

# Pesos para la confianza combinada
_W_OCR = 0.60
_W_CAMPOS = 0.40


@dataclass
class ActaOCRResult:
    """Resultado completo del procesamiento OCR de un acta electoral."""

    # Campos extraídos del formulario (clave → valor tipado)
    campos: Dict[str, Any] = field(default_factory=dict)

    # Métricas de calidad
    confianza_ocr: float = 0.0        # promedio de confianza de palabras Tesseract (0-1)
    confianza_campos: float = 0.0     # ratio de campos numéricos extraídos (0-1)
    confianza_combinada: float = 0.0  # promedio ponderado de las dos anteriores
    calidad_imagen: str = "BUENA"     # BUENA | REGULAR | MALA

    # Texto crudo devuelto por Tesseract (útil para auditoría)
    texto_crudo: str = ""

    # Metadatos del procesamiento
    fuente: str = "PDF"               # PDF | IMAGEN
    paginas_procesadas: int = 0
    errores_procesamiento: List[str] = field(default_factory=list)

    # ── Propiedades de conveniencia ───────────────────────────────────────────

    @property
    def supera_umbral(self) -> bool:
        """True si la confianza supera el umbral mínimo del validador (75 %)."""
        return self.confianza_combinada >= 0.75

    @property
    def es_procesable(self) -> bool:
        """True si la imagen tiene calidad mínima para OCR."""
        return self.calidad_imagen != "MALA"

    # ── Conversión al contrato del validador RRV ──────────────────────────────

    def to_acta_rrv_dict(self) -> dict:
        """
        Devuelve un dict compatible con ActaRRVInput para pasarlo al validador.

        Los campos no extraídos se rellenan con valores seguros (0 / "DESCONOCIDO")
        para que Pydantic no rechace el objeto; el validador los detectará como
        OBSERVADA si no cuadran numéricamente.
        """
        c = self.campos

        # mesa_codigo: preferir el código de mesa, si no usar el nro de mesa
        nro = c.get("nro_mesa", 0)
        mesa_codigo = c.get("codigo_mesa") or str(nro) or "DESCONOCIDO"

        return {
            # Identificación
            "mesa_codigo": mesa_codigo,
            "nro_mesa": nro if isinstance(nro, int) else 0,
            "codigo_recinto": c.get("codigo_recinto", "DESCONOCIDO"),
            "recinto_nombre": c.get("recinto_nombre"),
            "codigo_territorial": c.get("codigo_territorial", "DESCONOCIDO"),
            "departamento": c.get("departamento"),
            "provincia": c.get("provincia"),
            "municipio": c.get("municipio"),

            # Origen siempre OCR para este pipeline
            "origen": "OCR",
            "fuente": self.fuente,

            # Votos por partido (default 0 si no se extrajo)
            "partido_1_votos": c.get("partido_1_votos", 0),
            "partido_2_votos": c.get("partido_2_votos", 0),
            "partido_3_votos": c.get("partido_3_votos", 0),
            "partido_4_votos": c.get("partido_4_votos", 0),

            # Totales
            "votos_validos": c.get("votos_validos", 0),
            "votos_blancos": c.get("votos_blancos", 0),
            "votos_nulos": c.get("votos_nulos", 0),
            "votos_emitidos": c.get("votos_emitidos", 0),
            "boletas_no_utilizadas": c.get("boletas_no_utilizadas", 0),
            "total_boletas": c.get("total_boletas", 0),
            "nro_votantes": c.get("nro_votantes", 0),

            # Métricas OCR — el validador las usa para decidir OBSERVADA
            "confianza_ocr": round(self.confianza_combinada, 4),
            "calidad_imagen": self.calidad_imagen,
        }

    def to_metricas_dict(self) -> dict:
        return {
            "confianza_ocr": round(self.confianza_ocr, 4),
            "confianza_campos": round(self.confianza_campos, 4),
            "confianza_combinada": round(self.confianza_combinada, 4),
            "calidad_imagen": self.calidad_imagen,
            "paginas_procesadas": self.paginas_procesadas,
            "supera_umbral_75": self.supera_umbral,
        }


class OCRService:
    """
    Servicio OCR para extracción de datos de actas electorales bolivianas.

    Uso:
        service = OCRService()
        result = service.process_pdf(pdf_bytes)
        acta = result.to_acta_rrv_dict()
    """

    # DPI para conversión PDF → imagen  (300 dpi = calidad documental estándar)
    PDF_DPI = 300

    # PSM 6 = bloque uniforme (mejor balance para actas electorales bolivianas)
    TESSERACT_CONFIG = "--oem 3 --psm 6 -l spa"

    def __init__(self) -> None:
        self._preprocessor = ImagePreprocessor()
        self._parser = FormParser()

    # ── Puntos de entrada públicos ────────────────────────────────────────────

    def process_pdf(self, pdf_bytes: bytes) -> ActaOCRResult:
        """Convierte un PDF a imágenes y procesa la página de mayor confianza."""
        try:
            images = self._pdf_to_images(pdf_bytes)
        except ImportError:
            msg = (
                "pdf2image no está instalado o poppler no está en el PATH. "
                "Instalar: pip install pdf2image  y  poppler (winget / apt / brew)."
            )
            logger.error(msg)
            return ActaOCRResult(
                fuente="PDF",
                calidad_imagen="MALA",
                errores_procesamiento=[msg],
            )
        except Exception as exc:
            msg = f"Error al convertir PDF a imagen: {exc}"
            logger.error(msg)
            return ActaOCRResult(
                fuente="PDF",
                calidad_imagen="MALA",
                errores_procesamiento=[msg],
            )

        if not images:
            return ActaOCRResult(
                fuente="PDF",
                calidad_imagen="MALA",
                errores_procesamiento=["El PDF no contiene páginas procesables."],
            )

        # Procesar todas las páginas y conservar la de mayor confianza
        best: Optional[ActaOCRResult] = None
        for img in images:
            result = self._process_image_internal(img, fuente="PDF")
            if best is None or result.confianza_combinada > best.confianza_combinada:
                best = result

        best.paginas_procesadas = len(images)  # type: ignore[union-attr]
        return best  # type: ignore[return-value]

    def process_pdf_with_filename(self, pdf_bytes: bytes, filename: str) -> ActaOCRResult:
        """Como process_pdf pero también enriquece con datos del nombre de archivo."""
        result = self.process_pdf(pdf_bytes)
        _enrich_from_filename(result, filename)
        return result

    def process_image(self, image_bytes: bytes, filename: str = "") -> ActaOCRResult:
        """Procesa directamente un archivo de imagen (JPG, PNG, TIFF, BMP)."""
        fuente = "PDF" if filename.lower().endswith(".pdf") else "IMAGEN"
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            msg = f"Error al abrir imagen: {exc}"
            logger.error(msg)
            return ActaOCRResult(
                fuente=fuente,
                calidad_imagen="MALA",
                errores_procesamiento=[msg],
            )

        result = self._process_image_internal(img, fuente=fuente)
        result.paginas_procesadas = 1
        _enrich_from_filename(result, filename)
        return result

    # ── Pipeline interno ──────────────────────────────────────────────────────

    def _process_image_internal(
        self, image: Image.Image, fuente: str
    ) -> ActaOCRResult:
        result = ActaOCRResult(fuente=fuente)

        # 1. Preprocesamiento de imagen
        try:
            processed_img, calidad = self._preprocessor.preprocess(image)
            result.calidad_imagen = calidad
        except Exception as exc:
            msg = f"Error en preprocesamiento: {exc}"
            logger.warning(msg)
            result.errores_procesamiento.append(msg)
            processed_img = image
            result.calidad_imagen = "MALA"

        # 2. OCR con Tesseract
        try:
            import pytesseract

            result.texto_crudo = pytesseract.image_to_string(
                processed_img, config=self.TESSERACT_CONFIG
            )

            ocr_data = pytesseract.image_to_data(
                processed_img,
                config=self.TESSERACT_CONFIG,
                output_type=pytesseract.Output.DICT,
            )
            confidences = [
                int(c)
                for c in ocr_data["conf"]
                if str(c).lstrip("-").isdigit() and int(c) >= 0
            ]
            result.confianza_ocr = (
                sum(confidences) / len(confidences) / 100.0
                if confidences else 0.0
            )

        except ImportError:
            msg = (
                "pytesseract no está instalado. "
                "Instalar: pip install pytesseract  y  Tesseract-OCR."
            )
            logger.error(msg)
            result.errores_procesamiento.append(msg)
            return result
        except Exception as exc:
            msg = f"Error en OCR Tesseract: {exc}"
            logger.error(msg)
            result.errores_procesamiento.append(msg)
            return result

        # 3. Extracción de campos del formulario
        try:
            campos, confianza_campos = self._parser.parse(result.texto_crudo)
            result.campos = campos
            result.confianza_campos = confianza_campos
        except Exception as exc:
            msg = f"Error en parser de formulario: {exc}"
            logger.error(msg)
            result.errores_procesamiento.append(msg)

        # 4. Confianza combinada
        result.confianza_combinada = round(
            _W_OCR * result.confianza_ocr + _W_CAMPOS * result.confianza_campos, 4
        )

        logger.info(
            "OCR completado — calidad=%s confianza_ocr=%.0f%% "
            "confianza_campos=%.0f%% combinada=%.0f%%",
            result.calidad_imagen,
            result.confianza_ocr * 100,
            result.confianza_campos * 100,
            result.confianza_combinada * 100,
        )
        return result

    # ── Conversión PDF → imágenes ─────────────────────────────────────────────

    def _pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        from pdf2image import convert_from_bytes

        return convert_from_bytes(
            pdf_bytes,
            dpi=self.PDF_DPI,
            fmt="png",
            thread_count=2,
        )


# ── Enriquecimiento desde nombre de archivo ───────────────────────────────────

import re as _re


def _enrich_from_filename(result: ActaOCRResult, filename: str) -> None:
    """
    Extrae el código de acta del nombre de archivo si el OCR no lo obtuvo.

    Patrón esperado: acta_2020600556001.pdf → codigo_mesa = "2020600556001"
    """
    if not filename:
        return

    m = _re.search(r"(20\d{11})", filename)
    if not m:
        return

    codigo = m.group(1)

    # Solo enriquecer si el parser no obtuvo ya un código confiable
    if "codigo_mesa" not in result.campos:
        result.campos["codigo_mesa"] = codigo
        logger.info("codigo_mesa extraido del filename: %s", codigo)

    # Derivar nro_mesa de los últimos 3 dígitos del código si no está presente
    if "nro_mesa" not in result.campos:
        result.campos["nro_mesa"] = int(codigo[-3:])

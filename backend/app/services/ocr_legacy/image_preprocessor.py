"""
Preprocesador de imágenes para mejorar la calidad OCR de actas electorales.

Aplica:
  - Conversión a escala de grises
  - Reducción de ruido (filtro mediana)
  - Mejora de contraste (CLAHE)
  - Corrección de inclinación (deskew)
  - Binarización adaptativa
  - Evaluación de calidad: BUENA | REGULAR | MALA
"""

from __future__ import annotations

import logging
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class CalidadImagen:
    BUENA = "BUENA"
    REGULAR = "REGULAR"
    MALA = "MALA"


class ImagePreprocessor:
    """
    Preprocesa imágenes de actas electorales para maximizar la precisión OCR.

    La calidad se evalúa antes del procesamiento usando métricas de nitidez
    (varianza del Laplaciano) y contraste (desviación estándar de píxeles).
    """

    # Umbrales de nitidez (varianza Laplaciano)
    SHARPNESS_BUENA = 80.0
    SHARPNESS_REGULAR = 20.0

    # Umbrales de contraste (std de píxeles 0-255)
    CONTRAST_BUENA = 45.0
    CONTRAST_REGULAR = 15.0

    # Ángulo mínimo de inclinación para aplicar corrección
    DESKEW_THRESHOLD_DEG = 0.5

    def preprocess(self, image: Image.Image) -> Tuple[Image.Image, str]:
        """
        Preprocesa la imagen y evalúa su calidad.

        Para imágenes BUENAS retorna la imagen en escala de grises sin binarizar,
        ya que Tesseract rinde mejor sobre grises de alta calidad que sobre
        imágenes binarizadas agresivamente.

        Returns:
            (imagen_procesada, calidad): calidad ∈ {BUENA, REGULAR, MALA}
        """
        img_array = self._to_numpy(image)
        gray = self._to_grayscale(img_array)

        calidad = self._assess_quality(gray)
        logger.debug("Calidad evaluada: %s", calidad)

        if calidad == CalidadImagen.BUENA:
            # Imagen de alta calidad: solo denoise leve + corrección inclinación
            denoised = self._denoise(gray)
            deskewed = self._deskew(denoised)
            return Image.fromarray(deskewed), calidad

        if calidad == CalidadImagen.REGULAR:
            # Imagen media: pipeline completo con CLAHE + binarización suave
            denoised = self._denoise(gray)
            enhanced = self._enhance_contrast(denoised)
            deskewed = self._deskew(enhanced)
            binarized = self._binarize_adaptive(deskewed)
            return Image.fromarray(binarized), calidad

        # Imagen MALA: umbralización Otsu como último recurso
        binarized = self._binarize_otsu(gray)
        return Image.fromarray(binarized), calidad

    # ── Evaluación de calidad ─────────────────────────────────────────────────

    def _assess_quality(self, gray: np.ndarray) -> str:
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        contrast = float(gray.std())

        if sharpness >= self.SHARPNESS_BUENA and contrast >= self.CONTRAST_BUENA:
            return CalidadImagen.BUENA
        if sharpness >= self.SHARPNESS_REGULAR and contrast >= self.CONTRAST_REGULAR:
            return CalidadImagen.REGULAR
        return CalidadImagen.MALA

    # ── Pasos del pipeline ────────────────────────────────────────────────────

    def _denoise(self, gray: np.ndarray) -> np.ndarray:
        """Filtro mediana 3×3 — elimina ruido de sal y pimienta."""
        return cv2.medianBlur(gray, 3)

    def _enhance_contrast(self, gray: np.ndarray) -> np.ndarray:
        """CLAHE: normalización local de contraste."""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def _deskew(self, gray: np.ndarray) -> np.ndarray:
        """Corrige la inclinación detectando líneas horizontales con Hough."""
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

        if lines is None:
            return gray

        angles = []
        for line in lines[:30]:
            rho, theta = line[0]
            angle = np.degrees(theta) - 90.0
            if abs(angle) < 45.0:
                angles.append(angle)

        if not angles:
            return gray

        median_angle = float(np.median(angles))
        if abs(median_angle) < self.DESKEW_THRESHOLD_DEG:
            return gray

        h, w = gray.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), median_angle, 1.0)
        return cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def _binarize_adaptive(self, gray: np.ndarray) -> np.ndarray:
        """Umbralización adaptativa gaussiana — ideal para iluminación no uniforme."""
        return cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2,
        )

    def _binarize_otsu(self, gray: np.ndarray) -> np.ndarray:
        """Umbralización Otsu — fallback para imágenes de baja calidad."""
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    # ── Utilidades ────────────────────────────────────────────────────────────

    @staticmethod
    def _to_numpy(image: Image.Image) -> np.ndarray:
        return np.array(image.convert("RGB"))

    @staticmethod
    def _to_grayscale(img_array: np.ndarray) -> np.ndarray:
        if len(img_array.shape) == 2:
            return img_array
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

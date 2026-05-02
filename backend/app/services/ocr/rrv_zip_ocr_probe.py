from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import cv2
import fitz
import numpy as np
import pytesseract
from PIL import Image, ImageDraw

try:
    import easyocr
except Exception:
    easyocr = None


OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "spa")
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")


class RRVZipOCRProbe:
    TEMPLATE_WIDTH = 1400
    TEMPLATE_HEIGHT = 800

    def __init__(self):
        if TESSERACT_CMD and Path(TESSERACT_CMD).exists():
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

        self.easy_reader = None

    def get_easy_reader(self):
        if easyocr is None:
            return None

        if self.easy_reader is None:
            self.easy_reader = easyocr.Reader(["es", "en"], gpu=False)

        return self.easy_reader

    def detect_content_type(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return "application/pdf"

        if suffix in [".jpg", ".jpeg"]:
            return "image/jpeg"

        if suffix == ".png":
            return "image/png"

        return "application/octet-stream"

    def image_from_pdf(self, file_path: Path) -> Image.Image:
        document = fitz.open(str(file_path))
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        document.close()
        return image

    def load_image(self, file_path: Path) -> Image.Image:
        content_type = self.detect_content_type(file_path)

        if content_type == "application/pdf":
            return self.image_from_pdf(file_path)

        return Image.open(file_path).convert("RGB")

    def pil_to_cv(self, pil_image: Image.Image) -> np.ndarray:
        image_np = np.array(pil_image.convert("RGB"))
        return cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

    def cv_to_pil(self, image_np: np.ndarray) -> Image.Image:
        if len(image_np.shape) == 2:
            return Image.fromarray(image_np)

        image_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
        return Image.fromarray(image_rgb)

    def crop_ratio(self, pil_image: Image.Image, x1: float, y1: float, x2: float, y2: float) -> Image.Image:
        width, height = pil_image.size

        return pil_image.crop((
            int(width * x1),
            int(height * y1),
            int(width * x2),
            int(height * y2),
        ))

    def save_debug_image(self, debug_dir: Path, name: str, pil_image: Image.Image, subfolder: str | None = None) -> str:
        output_dir = debug_dir

        if subfolder:
            output_dir = output_dir / subfolder

        output_dir.mkdir(parents=True, exist_ok=True)

        path = output_dir / f"{name}.png"
        pil_image.save(path)

        return str(path).replace("\\", "/")

    def save_debug_text(self, debug_dir: Path, name: str, text: str) -> str:
        debug_dir.mkdir(parents=True, exist_ok=True)
        path = debug_dir / f"{name}.txt"
        path.write_text(text or "", encoding="utf-8")
        return str(path).replace("\\", "/")

    def analyze_quality(self, pil_image: Image.Image) -> dict:
        image_np = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        brightness = float(np.mean(gray))

        return {
            "blurScore": round(float(blur_score), 2),
            "brightness": round(brightness, 2),
        }

    def order_points(self, points: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype="float32")

        points_sum = points.sum(axis=1)
        points_diff = np.diff(points, axis=1)

        rect[0] = points[np.argmin(points_sum)]
        rect[2] = points[np.argmax(points_sum)]
        rect[1] = points[np.argmin(points_diff)]
        rect[3] = points[np.argmax(points_diff)]

        return rect

    def align_acta_image(self, pil_image: Image.Image, debug_dir: Path) -> tuple[Image.Image, dict]:
        image_bgr = self.pil_to_cv(pil_image)
        original = image_bgr.copy()

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        edges = cv2.Canny(gray, 50, 150)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        image_area = image_bgr.shape[0] * image_bgr.shape[1]
        best_quad = None
        best_area = 0

        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(contour)

            if area < image_area * 0.20:
                continue

            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

            if len(approx) == 4 and area > best_area:
                best_quad = approx.reshape(4, 2).astype("float32")
                best_area = area

        if best_quad is None:
            orig_h, orig_w = original.shape[:2]
            new_h = int(orig_h * self.TEMPLATE_WIDTH / orig_w)

            resized = cv2.resize(
                original,
                (self.TEMPLATE_WIDTH, new_h),
                interpolation=cv2.INTER_CUBIC,
            )

            aligned = self.cv_to_pil(resized)
            self.save_debug_image(debug_dir, "ALIGNED_ACTA_FALLBACK_RESIZE", aligned)

            return aligned, {
                "aligned": False,
                "method": "fallback_resize",
                "reason": "NO_DOCUMENT_CONTOUR",
            }

        rect = self.order_points(best_quad)

        destination = np.array([
            [0, 0],
            [self.TEMPLATE_WIDTH - 1, 0],
            [self.TEMPLATE_WIDTH - 1, self.TEMPLATE_HEIGHT - 1],
            [0, self.TEMPLATE_HEIGHT - 1],
        ], dtype="float32")

        matrix = cv2.getPerspectiveTransform(rect, destination)

        warped = cv2.warpPerspective(
            original,
            matrix,
            (self.TEMPLATE_WIDTH, self.TEMPLATE_HEIGHT),
        )

        aligned = self.cv_to_pil(warped)
        self.save_debug_image(debug_dir, "ALIGNED_ACTA", aligned)

        return aligned, {
            "aligned": True,
            "method": "perspective_warp",
            "contourArea": round(float(best_area), 2),
        }

    def inspect_pdf_text(self, file_path: Path) -> str:
        if file_path.suffix.lower() != ".pdf":
            return ""

        try:
            document = fitz.open(str(file_path))
            pages_text = []

            for page in document:
                pages_text.append(page.get_text("text"))

            document.close()

            return "\n".join(pages_text).strip()
        except Exception:
            return ""

    def normalize_digit_text(self, text: str) -> str:
        replacements = {
            "O": "0",
            "o": "0",
            "Q": "0",
            "D": "0",
            "I": "1",
            "l": "1",
            "|": "1",
            "!": "1",
            "S": "5",
            "s": "5",
            "B": "8",
            "b": "8",
            "Z": "2",
            "z": "2",
        }

        normalized = ""

        for char in text or "":
            if char.isdigit():
                normalized += char
            elif char in replacements:
                normalized += replacements[char]

        return normalized

    def preprocess_for_ocr(self, pil_image: Image.Image) -> np.ndarray:
        image_np = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

        gray = cv2.resize(
            gray,
            None,
            fx=2,
            fy=2,
            interpolation=cv2.INTER_CUBIC,
        )

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        denoised = cv2.fastNlMeansDenoising(enhanced, None, 20, 7, 21)

        threshold = cv2.threshold(
            denoised,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )[1]

        return threshold

    def run_tesseract(self, pil_image: Image.Image, psm: int = 6, whitelist: str | None = None) -> tuple[str, float, list[str]]:
        try:
            processed = self.preprocess_for_ocr(pil_image)

            config = f"--oem 3 --psm {psm}"

            if whitelist:
                config += f" -c tessedit_char_whitelist={whitelist}"

            data = pytesseract.image_to_data(
                processed,
                lang=OCR_LANGUAGE,
                config=config,
                output_type=pytesseract.Output.DICT,
            )

            words = []
            confidences = []

            for index, text in enumerate(data.get("text", [])):
                clean_text = str(text).strip()

                if clean_text:
                    words.append(clean_text)

                    try:
                        confidence = float(data["conf"][index])

                        if confidence >= 0:
                            confidences.append(confidence)
                    except Exception:
                        pass

            full_text = " ".join(words)

            avg_confidence = (
                round(sum(confidences) / len(confidences) / 100, 2)
                if confidences
                else 0
            )

            return full_text, avg_confidence, []

        except Exception as error:
            return "", 0, [f"OCR_ENGINE_ERROR: {str(error)}"]

    def detect_qr(self, pil_image: Image.Image) -> dict:
        image_np = np.array(pil_image.convert("RGB"))
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(image_np)

        if not data:
            return {
                "detectado": False,
                "contenido": None,
                "codigoMesaQr": None,
                "coincideConMesa": False,
            }

        codigo_mesa_qr = None

        if "MESA:" in data:
            try:
                codigo_mesa_qr = data.split("MESA:")[1].split("|")[0].strip()
            except Exception:
                codigo_mesa_qr = None

        return {
            "detectado": True,
            "contenido": data,
            "codigoMesaQr": codigo_mesa_qr,
            "coincideConMesa": False,
        }

    def extract_digits_by_easyocr(self, pil_image: Image.Image, expected_digits: int | None = None) -> str | None:
        reader = self.get_easy_reader()

        if reader is None:
            return None

        try:
            image_np = np.array(pil_image.convert("RGB"))

            result = reader.readtext(
                image_np,
                detail=1,
                allowlist="0123456789",
                paragraph=False,
                decoder="greedy",
            )

            candidates = []

            for item in result:
                text = str(item[1])
                confidence = float(item[2])

                if confidence < 0.35:
                    continue

                digits = "".join(char for char in text if char.isdigit())

                if not digits:
                    continue

                if expected_digits is None:
                    candidates.append((digits, confidence))
                elif len(digits) == expected_digits:
                    candidates.append((digits, confidence))
                elif len(digits) == expected_digits - 1:
                    candidates.append((digits.zfill(expected_digits), confidence - 0.10))

            if not candidates:
                return None

            candidates.sort(key=lambda item: item[1], reverse=True)
            return candidates[0][0]

        except Exception:
            return None

    def preprocess_digit_cell_variants(self, pil_image: Image.Image) -> list[np.ndarray]:
        image_np = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

        gray = cv2.resize(
            gray,
            None,
            fx=12,
            fy=12,
            interpolation=cv2.INTER_CUBIC,
        )

        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        binary_inv = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )[1]

        height, width = binary_inv.shape

        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (max(10, width // 2), 1),
        )

        vertical_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (1, max(10, height // 2)),
        )

        horizontal_lines = cv2.morphologyEx(binary_inv, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
        vertical_lines = cv2.morphologyEx(binary_inv, cv2.MORPH_OPEN, vertical_kernel, iterations=1)

        grid_lines = cv2.bitwise_or(horizontal_lines, vertical_lines)
        clean_digits = cv2.subtract(binary_inv, grid_lines)

        small_kernel = np.ones((2, 2), np.uint8)

        clean_digits = cv2.morphologyEx(clean_digits, cv2.MORPH_CLOSE, small_kernel, iterations=1)
        clean_digits = cv2.dilate(clean_digits, small_kernel, iterations=1)

        normal = cv2.bitwise_not(clean_digits)

        adaptive = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            9,
        )

        variants = [
            normal,
            adaptive,
            cv2.bitwise_not(binary_inv),
        ]

        prepared = []

        for variant in variants:
            padded = cv2.copyMakeBorder(
                variant,
                40,
                40,
                40,
                40,
                cv2.BORDER_CONSTANT,
                value=255,
            )
            prepared.append(padded)

        return prepared

    def isolate_digit_on_canvas(self, pil_image: Image.Image) -> Image.Image:
        image_np = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

        gray = cv2.resize(gray, None, fx=12, fy=12, interpolation=cv2.INTER_CUBIC)

        h, w = gray.shape

        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            9,
        )

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        canvas_h, canvas_w = 120, 80
        canvas = np.ones((canvas_h, canvas_w), dtype=np.uint8) * 255

        if not contours:
            return Image.fromarray(canvas)

        digit_contours = []

        for contour in contours:
            _, _, contour_w, contour_h = cv2.boundingRect(contour)

            if cv2.contourArea(contour) < 30:
                continue

            if contour_w > w * 0.85:
                continue

            if contour_h < max(5, int(h * 0.12)):
                continue

            digit_contours.append(contour)

        if not digit_contours:
            digit_contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]

        if not digit_contours:
            return Image.fromarray(canvas)

        x_min = min(cv2.boundingRect(contour)[0] for contour in digit_contours)
        y_min = min(cv2.boundingRect(contour)[1] for contour in digit_contours)
        x_max = max(cv2.boundingRect(contour)[0] + cv2.boundingRect(contour)[2] for contour in digit_contours)
        y_max = max(cv2.boundingRect(contour)[1] + cv2.boundingRect(contour)[3] for contour in digit_contours)

        if x_max <= x_min or y_max <= y_min:
            return Image.fromarray(canvas)

        binary_bw = cv2.bitwise_not(binary)
        digit_region = binary_bw[y_min:y_max, x_min:x_max]

        digit_h, digit_w = digit_region.shape[:2]

        if digit_w == 0 or digit_h == 0:
            return Image.fromarray(canvas)

        margin = 10
        scale = min(
            (canvas_w - 2 * margin) / digit_w,
            (canvas_h - 2 * margin) / digit_h,
        )

        new_w = max(1, int(digit_w * scale))
        new_h = max(1, int(digit_h * scale))

        scaled = cv2.resize(digit_region, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        x_offset = (canvas_w - new_w) // 2
        y_offset = (canvas_h - new_h) // 2

        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = scaled

        return Image.fromarray(canvas)

    def read_single_digit_cell_with_tesseract(self, pil_image: Image.Image) -> str | None:
        variants = self.preprocess_digit_cell_variants(pil_image)
        candidates = []

        for variant in variants:
            for psm in [10, 13, 8]:
                config = (
                    f"--oem 3 --psm {psm} "
                    "-c tessedit_char_whitelist=0123456789OoIl|!SsBbZz"
                )

                try:
                    text = pytesseract.image_to_string(
                        variant,
                        lang=OCR_LANGUAGE,
                        config=config,
                    )

                    normalized = self.normalize_digit_text(text)

                    if len(normalized) == 1:
                        candidates.append(normalized[0])
                except Exception:
                    pass

        if candidates:
            return max(set(candidates), key=candidates.count)

        return None

    def read_single_digit_cell_with_easyocr(self, pil_image: Image.Image) -> str | None:
        reader = self.get_easy_reader()

        if reader is None:
            return None

        try:
            image_np = np.array(pil_image.convert("RGB"))

            result = reader.readtext(
                image_np,
                detail=1,
                allowlist="0123456789",
            )

            candidates = []

            for item in result:
                text = str(item[1])
                confidence = float(item[2])

                if confidence < 0.40:
                    continue

                digits = "".join(char for char in text if char.isdigit())

                if len(digits) == 1:
                    candidates.append(digits)

            if candidates:
                return max(set(candidates), key=candidates.count)

        except Exception:
            pass

        return None

    def read_single_digit_cell(self, pil_image: Image.Image) -> str | None:
        isolated = self.isolate_digit_on_canvas(pil_image)
        isolated_np = np.array(isolated)

        padded = cv2.copyMakeBorder(
            isolated_np,
            20,
            20,
            20,
            20,
            cv2.BORDER_CONSTANT,
            value=255,
        )

        candidates = []

        for psm in [10, 8, 13]:
            config = (
                f"--oem 3 --psm {psm} "
                "-c tessedit_char_whitelist=0123456789OoIl|!SsBbZz"
            )

            try:
                text = pytesseract.image_to_string(
                    Image.fromarray(padded),
                    lang=OCR_LANGUAGE,
                    config=config,
                )

                normalized = self.normalize_digit_text(text)

                if len(normalized) == 1:
                    candidates.append(normalized[0])
            except Exception:
                pass

        if candidates:
            return max(set(candidates), key=candidates.count)

        digit = self.read_single_digit_cell_with_tesseract(pil_image)

        if digit is not None:
            return digit

        return self.read_single_digit_cell_with_easyocr(pil_image)

    def read_group_highres_ocr(self, pil_image: Image.Image, expected_digits: int = 3) -> int | None:
        try:
            image_np = np.array(pil_image.convert("RGB"))
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

            gray = cv2.resize(gray, None, fx=12, fy=12, interpolation=cv2.INTER_CUBIC)
            gray = cv2.GaussianBlur(gray, (3, 3), 0)

            binary = cv2.threshold(
                gray,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )[1]

            padded = cv2.copyMakeBorder(
                binary,
                40,
                40,
                40,
                40,
                cv2.BORDER_CONSTANT,
                value=255,
            )

            candidates = []

            for psm in [7, 8, 13]:
                config = (
                    f"--oem 3 --psm {psm} "
                    "-c tessedit_char_whitelist=0123456789OoIl|!SsBbZz"
                )

                text = pytesseract.image_to_string(
                    padded,
                    lang=OCR_LANGUAGE,
                    config=config,
                )

                normalized = self.normalize_digit_text(text)

                if len(normalized) == expected_digits:
                    candidates.append(normalized)

            if candidates:
                return int(max(set(candidates), key=candidates.count))

        except Exception:
            pass

        easy_digits = self.extract_digits_by_easyocr(pil_image, expected_digits)

        if easy_digits is not None:
            return int(easy_digits)

        return None

    def read_group_digits_by_cells(
        self,
        pil_image: Image.Image,
        group_name: str,
        debug_dir: Path,
        expected_digits: int = 3,
    ) -> int | None:
        full_value = self.read_group_highres_ocr(pil_image, expected_digits)

        if full_value is not None:
            return full_value

        width, height = pil_image.size

        trim_top = int(height * 0.15)
        trim_bottom = int(height * 0.85)

        if trim_bottom > trim_top + 4:
            pil_for_cells = pil_image.crop((0, trim_top, width, trim_bottom))
        else:
            pil_for_cells = pil_image

        cell_width_total, cell_height = pil_for_cells.size
        digits = []

        cells_debug_dir = debug_dir / "boxed_votes" / "cells"
        cells_debug_dir.mkdir(parents=True, exist_ok=True)

        for index in range(expected_digits):
            cell_width = cell_width_total / expected_digits

            base_x1 = int(cell_width * index)
            base_x2 = int(cell_width * (index + 1))

            margins = [
                (0.10, 0.12),
                (0.16, 0.18),
                (0.06, 0.08),
                (0.02, 0.04),
            ]

            digit = None

            for attempt_index, (margin_x_ratio, margin_y_ratio) in enumerate(margins, start=1):
                margin_x = int(cell_width * margin_x_ratio)
                margin_y = int(cell_height * margin_y_ratio)

                x1 = max(0, base_x1 + margin_x)
                x2 = min(cell_width_total, base_x2 - margin_x)
                y1 = max(0, margin_y)
                y2 = min(cell_height, cell_height - margin_y)

                if x2 <= x1 or y2 <= y1:
                    continue

                cell = pil_for_cells.crop((x1, y1, x2, y2))
                cell.save(cells_debug_dir / f"{group_name}_cell_{index + 1}_try_{attempt_index}.png")

                digit = self.read_single_digit_cell(cell)

                if digit is not None:
                    break

            if digit is None:
                return None

            digits.append(digit)

        return int("".join(digits))

    def save_debug_crop_overlay(self, aligned_image: Image.Image, overlay_boxes: list, debug_dir: Path) -> str:
        overlay = aligned_image.copy().convert("RGB")
        draw = ImageDraw.Draw(overlay)
        width, height = overlay.size

        palette = ["red", "blue", "green", "orange", "purple", "cyan", "magenta"]

        for i, (label, x1r, y1r, x2r, y2r) in enumerate(overlay_boxes):
            color = palette[i % len(palette)]

            x1 = int(x1r * width)
            y1 = int(y1r * height)
            x2 = int(x2r * width)
            y2 = int(y2r * height)

            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            draw.text((x1 + 2, max(0, y1 - 12)), label, fill=color)

        output_dir = debug_dir / "boxed_votes"
        output_dir.mkdir(parents=True, exist_ok=True)

        path = output_dir / "DEBUG_CROP_OVERLAY.png"
        overlay.save(path)

        return str(path).replace("\\", "/")

    def extract_boxed_votes_from_real_acta(self, aligned_image: Image.Image, debug_dir: Path) -> dict:
        vote_x1 = 0.305
        vote_x2 = 0.420

        candidate_rows = [
            ("P1", "Partido 1", 0.331, 0.365),
            ("P2", "Partido 2", 0.355, 0.387),
            ("P3", "Partido 3", 0.377, 0.409),
            ("P4", "Partido 4", 0.400, 0.432),
        ]

        total_fields = [
            ("VOTOS_VALIDOS", 0.645, 0.715),
            ("VOTOS_BLANCOS", 0.730, 0.765),
            ("VOTOS_NULOS", 0.772, 0.838),
        ]

        boxed_dir = debug_dir / "boxed_votes"
        boxed_dir.mkdir(parents=True, exist_ok=True)

        candidatos = []
        boxed_regions = {}
        overlay_boxes = []

        for codigo, nombre, y1, y2 in candidate_rows:
            crop = self.crop_ratio(aligned_image, vote_x1, y1, vote_x2, y2)
            boxed_regions[codigo] = crop
            overlay_boxes.append((codigo, vote_x1, y1, vote_x2, y2))
            crop.save(boxed_dir / f"{codigo}.png")

            value = self.read_group_digits_by_cells(
                crop,
                group_name=codigo,
                debug_dir=debug_dir,
                expected_digits=3,
            )

            if value is not None and 0 <= value <= 999:
                candidatos.append({
                    "partidoCodigo": codigo,
                    "partidoNombre": nombre,
                    "cantidadVotos": value,
                })

        total_values = {}

        for field_key, y1, y2 in total_fields:
            crop = self.crop_ratio(aligned_image, vote_x1, y1, vote_x2, y2)
            boxed_regions[field_key] = crop
            overlay_boxes.append((field_key.replace("VOTOS_", ""), vote_x1, y1, vote_x2, y2))
            crop.save(boxed_dir / f"{field_key}.png")

            total_values[field_key] = self.read_group_digits_by_cells(
                crop,
                group_name=field_key,
                debug_dir=debug_dir,
                expected_digits=3,
            )

        votos_validos = total_values.get("VOTOS_VALIDOS")
        votos_blancos = total_values.get("VOTOS_BLANCOS")
        votos_nulos = total_values.get("VOTOS_NULOS")

        total_votos = None

        if votos_validos is not None and votos_blancos is not None and votos_nulos is not None:
            total_votos = votos_validos + votos_blancos + votos_nulos

        overlay_path = self.save_debug_crop_overlay(aligned_image, overlay_boxes, debug_dir)

        return {
            "votosPartidos": candidatos,
            "votosValidos": votos_validos,
            "votosBlancos": votos_blancos,
            "votosNulos": votos_nulos,
            "totalVotos": total_votos,
            "sumaPartidos": sum(item["cantidadVotos"] for item in candidatos),
            "debugOverlay": overlay_path,
        }

    def extract_text_regions(self, aligned_image: Image.Image, debug_dir: Path) -> dict:
        regions = {
            "GLOBAL": self.crop_ratio(aligned_image, 0.00, 0.00, 1.00, 1.00),
            "INFO_IZQUIERDA": self.crop_ratio(aligned_image, 0.00, 0.10, 0.28, 0.78),
            "CANDIDATOS": self.crop_ratio(aligned_image, 0.16, 0.27, 0.48, 0.58),
            "TOTALES": self.crop_ratio(aligned_image, 0.22, 0.48, 0.56, 0.78),
            "QR": self.crop_ratio(aligned_image, 0.08, 0.00, 0.30, 0.18),
        }

        debug_files = {}

        for name, image in regions.items():
            debug_files[name] = self.save_debug_image(debug_dir, name, image)

        texts = {}
        confidences = []
        errors = []

        for name, psm in [
            ("GLOBAL", 11),
            ("INFO_IZQUIERDA", 6),
            ("CANDIDATOS", 6),
            ("TOTALES", 6),
        ]:
            text, confidence, local_errors = self.run_tesseract(regions[name], psm=psm)
            texts[name] = text
            errors.extend(local_errors)

            if confidence > 0:
                confidences.append(confidence)

        combined_text = "\n".join([
            "[INFO_IZQUIERDA]",
            texts.get("INFO_IZQUIERDA", ""),
            "[CANDIDATOS]",
            texts.get("CANDIDATOS", ""),
            "[TOTALES]",
            texts.get("TOTALES", ""),
            "[GLOBAL]",
            texts.get("GLOBAL", ""),
        ])

        confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0

        self.save_debug_text(debug_dir, "COMBINED_TEXT", combined_text)

        return {
            "regions": regions,
            "debugFiles": debug_files,
            "texts": texts,
            "combinedText": combined_text,
            "confidence": confidence,
            "errors": errors,
        }

    def extract_location_fields(self, aligned_image: Image.Image, debug_dir: Path) -> dict:
        crops = {
            "mesa_codigo": self.crop_ratio(aligned_image, 0.055, 0.165, 0.185, 0.230),
            "departamento": self.crop_ratio(aligned_image, 0.240, 0.163, 0.390, 0.180),
            "provincia": self.crop_ratio(aligned_image, 0.240, 0.180, 0.390, 0.193),
            "municipio": self.crop_ratio(aligned_image, 0.240, 0.193, 0.390, 0.207),
            "recinto_nombre": self.crop_ratio(aligned_image, 0.240, 0.207, 0.455, 0.222),
            "recinto_direccion": self.crop_ratio(aligned_image, 0.240, 0.222, 0.640, 0.252),
            "nro_mesa": self.crop_ratio(aligned_image, 0.060, 0.330, 0.155, 0.455),
            "nro_votantes": self.crop_ratio(aligned_image, 0.062, 0.725, 0.155, 0.770),
            "total_boletas": self.crop_ratio(aligned_image, 0.075, 0.805, 0.165, 0.855),
            "boletas_no_utilizadas": self.crop_ratio(aligned_image, 0.075, 0.895, 0.165, 0.950),
            "apertura_hora": self.crop_ratio(aligned_image, 0.060, 0.505, 0.105, 0.555),
            "apertura_minutos": self.crop_ratio(aligned_image, 0.108, 0.505, 0.165, 0.555),
            "cierre_hora": self.crop_ratio(aligned_image, 0.060, 0.645, 0.105, 0.695),
            "cierre_minutos": self.crop_ratio(aligned_image, 0.108, 0.645, 0.165, 0.695),
        }

        crops_dir = debug_dir / "direct_fields"
        crops_dir.mkdir(parents=True, exist_ok=True)

        for name, crop in crops.items():
            crop.save(crops_dir / f"{name}.png")

        def text_crop(name: str, psm: int = 7) -> str | None:
            text, _, _ = self.run_tesseract(crops[name], psm=psm)
            text = re.sub(r"\s+", " ", text or "").strip()
            return text or None

        def digits_crop(name: str, expected_digits: int) -> int | None:
            crop = crops[name]

            value = self.read_group_highres_ocr(crop, expected_digits)

            if value is not None:
                return value

            value = self.read_group_digits_by_cells(
                crop,
                group_name=name,
                debug_dir=debug_dir,
                expected_digits=expected_digits,
            )

            return value

        mesa_codigo_raw = self.extract_digits_by_easyocr(crops["mesa_codigo"], 13)

        if mesa_codigo_raw is None:
            text, _, _ = self.run_tesseract(crops["mesa_codigo"], psm=7, whitelist="0123456789")
            digits = re.sub(r"\D", "", text)
            mesa_codigo_raw = digits if len(digits) >= 10 else None

        mesa_codigo = mesa_codigo_raw[:13] if mesa_codigo_raw and len(mesa_codigo_raw) >= 13 else mesa_codigo_raw

        return {
            "mesa_codigo": mesa_codigo,
            "codigo_territorial": mesa_codigo[:6] if mesa_codigo and len(mesa_codigo) >= 6 else None,
            "codigo_recinto": mesa_codigo[:10] if mesa_codigo and len(mesa_codigo) >= 10 else None,
            "nro_mesa": digits_crop("nro_mesa", 1),
            "departamento": text_crop("departamento"),
            "provincia": text_crop("provincia"),
            "municipio": text_crop("municipio"),
            "recinto_nombre": text_crop("recinto_nombre"),
            "recinto_direccion": text_crop("recinto_direccion", psm=6),
            "nro_votantes": digits_crop("nro_votantes", 3),
            "total_boletas": digits_crop("total_boletas", 3),
            "boletas_no_utilizadas": digits_crop("boletas_no_utilizadas", 3),
            "apertura_hora": digits_crop("apertura_hora", 2),
            "apertura_minutos": digits_crop("apertura_minutos", 2),
            "cierre_hora": digits_crop("cierre_hora", 2),
            "cierre_minutos": digits_crop("cierre_minutos", 2),
        }

    def process_file(self, file_path: str | Path, codigo_mesa: str | None = None, debug_root: str | Path = "storage/zip_ocr_probe") -> dict:
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"No existe el archivo: {file_path}")

        debug_id = codigo_mesa or file_path.stem
        debug_dir = Path(debug_root) / str(debug_id)
        debug_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()

        pdf_text = self.inspect_pdf_text(file_path)
        self.save_debug_text(debug_dir, "PDF_NATIVE_TEXT", pdf_text)

        original_image = self.load_image(file_path)
        self.save_debug_image(debug_dir, "ORIGINAL_IMAGE", original_image)

        quality = self.analyze_quality(original_image)

        aligned_image, alignment = self.align_acta_image(original_image, debug_dir)
        text_regions = self.extract_text_regions(aligned_image, debug_dir)
        direct_fields = self.extract_location_fields(aligned_image, debug_dir)
        boxed_votes = self.extract_boxed_votes_from_real_acta(aligned_image, debug_dir)

        qr = self.detect_qr(text_regions["regions"]["QR"])

        if codigo_mesa and qr.get("codigoMesaQr"):
            qr["coincideConMesa"] = str(qr["codigoMesaQr"]) == str(codigo_mesa)

        votos_partidos = boxed_votes.get("votosPartidos", [])

        p1 = next((item["cantidadVotos"] for item in votos_partidos if item["partidoCodigo"] == "P1"), None)
        p2 = next((item["cantidadVotos"] for item in votos_partidos if item["partidoCodigo"] == "P2"), None)
        p3 = next((item["cantidadVotos"] for item in votos_partidos if item["partidoCodigo"] == "P3"), None)
        p4 = next((item["cantidadVotos"] for item in votos_partidos if item["partidoCodigo"] == "P4"), None)

        result = {
            "source_image": str(file_path),
            "extractor": "rrv_zip_ocr_probe",
            "processed_at": now,

            "mesa_codigo": direct_fields.get("mesa_codigo"),
            "codigo_territorial": direct_fields.get("codigo_territorial"),
            "codigo_recinto": direct_fields.get("codigo_recinto"),
            "nro_mesa": direct_fields.get("nro_mesa"),
            "departamento": direct_fields.get("departamento"),
            "provincia": direct_fields.get("provincia"),
            "municipio": direct_fields.get("municipio"),
            "recinto_nombre": direct_fields.get("recinto_nombre"),
            "recinto_direccion": direct_fields.get("recinto_direccion"),

            "nro_votantes": direct_fields.get("nro_votantes"),
            "total_boletas": direct_fields.get("total_boletas"),
            "boletas_no_utilizadas": direct_fields.get("boletas_no_utilizadas"),

            "partido_1_votos": p1,
            "partido_2_votos": p2,
            "partido_3_votos": p3,
            "partido_4_votos": p4,
            "votos_validos": boxed_votes.get("votosValidos"),
            "votos_blancos": boxed_votes.get("votosBlancos"),
            "votos_nulos": boxed_votes.get("votosNulos"),
            "votos_emitidos": boxed_votes.get("totalVotos"),
            "votos_emitidos_origen": "CALCULADO" if boxed_votes.get("totalVotos") is not None else "NO_CALCULADO",

            "apertura_hora": direct_fields.get("apertura_hora"),
            "apertura_minutos": direct_fields.get("apertura_minutos"),
            "cierre_hora": direct_fields.get("cierre_hora"),
            "cierre_minutos": direct_fields.get("cierre_minutos"),

            "quality": quality,
            "alignment": alignment,
            "qr": qr,
            "ocr_text_confidence": text_regions.get("confidence"),
            "ocr_errors": text_regions.get("errors", []),
            "debug_dir": str(debug_dir.resolve()).replace("\\", "/"),
            "debug_overlay": boxed_votes.get("debugOverlay"),
            "raw_boxed_votes": boxed_votes,
            "raw_combined_text": text_regions.get("combinedText"),
        }

        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--codigo-mesa", default=None)
    parser.add_argument("--output", default="rrv_zip_ocr_result.json")
    parser.add_argument("--debug-root", default="storage/zip_ocr_probe")
    args = parser.parse_args()

    service = RRVZipOCRProbe()

    result = service.process_file(
        file_path=args.input,
        codigo_mesa=args.codigo_mesa,
        debug_root=args.debug_root,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
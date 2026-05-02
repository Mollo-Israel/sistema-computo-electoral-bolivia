from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

try:
    import pytesseract
    _TESSERACT_OK = True
except ImportError:
    pytesseract = None
    _TESSERACT_OK = False


_DIGIT_WHITELIST = "0123456789"

_TEXT_LANG = os.getenv("TESSERACT_LANG", "spa")
_DIGIT_LANG = os.getenv("TESSERACT_DIGIT_LANG", "eng")

_CONF_OK = 0.60
_CONF_LOW = 0.30

_NUM_FIX: dict[str, str] = {
    "O": "0",
    "o": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "l": "1",
    "|": "1",
    "i": "1",
    "!": "1",
    "Z": "2",
    "S": "5",
    "s": "5",
    "B": "8",
    "b": "8",
    " ": "",
    "\n": "",
    "\t": "",
    ":": "",
    ".": "",
    ",": "",
}


@dataclass
class FieldOCRResult:
    value: str | None
    raw_text: str
    confidence: float
    status: str
    strategy: str


_NO_TESSERACT = FieldOCRResult(
    value=None,
    raw_text="",
    confidence=0.0,
    status="OCR_ERROR",
    strategy="no_tesseract",
)

_EMPTY = FieldOCRResult(
    value=None,
    raw_text="",
    confidence=0.0,
    status="CAMPO_VACIO",
    strategy="all_failed",
)


def _configure_tesseract() -> None:
    if not _TESSERACT_OK:
        return

    tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
    default_windows_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    elif default_windows_path.exists():
        pytesseract.pytesseract.tesseract_cmd = str(default_windows_path)


_configure_tesseract()


def _digit_cfg(psm: int) -> str:
    return (
        f"--psm {psm} --oem 3 "
        f"-c tessedit_char_whitelist={_DIGIT_WHITELIST} "
        "-c classify_bln_numeric_mode=1 "
        "-c load_system_dawg=0 "
        "-c load_freq_dawg=0"
    )


def _text_cfg(psm: int) -> str:
    return f"--psm {psm} --oem 3 -c preserve_interword_spaces=1"


def _safe_conf(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def _status_from(value: str | None, confidence: float) -> str:
    if not value:
        return "CAMPO_VACIO"
    if confidence < _CONF_LOW:
        return "BAJA_CONFIANZA"
    if confidence < _CONF_OK:
        return "BAJA_CONFIANZA"
    return "OK"


def _correct_digits(text: str) -> str:
    fixed = "".join(_NUM_FIX.get(c, c) for c in text)
    return re.sub(r"[^\d]", "", fixed)


def _clean_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def _ensure_bgr(img: np.ndarray) -> np.ndarray:
    if img is None:
        raise ValueError("Imagen vacía para OCR")

    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    return img


def _to_gray(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(_ensure_bgr(img), cv2.COLOR_BGR2GRAY)


def _clahe(gray: np.ndarray, clip: float = 2.0, tile: int = 8) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile))
    return clahe.apply(gray)


def _pad_white(img: np.ndarray, pad: int = 18) -> np.ndarray:
    if len(img.shape) == 2:
        return cv2.copyMakeBorder(
            img,
            pad,
            pad,
            pad,
            pad,
            cv2.BORDER_CONSTANT,
            value=255,
        )

    return cv2.copyMakeBorder(
        img,
        pad,
        pad,
        pad,
        pad,
        cv2.BORDER_CONSTANT,
        value=(255, 255, 255),
    )


def _resize_min(img: np.ndarray, min_w: int = 120, min_h: int = 120) -> np.ndarray:
    h, w = img.shape[:2]
    if h <= 0 or w <= 0:
        return img

    scale = max(min_w / w if w < min_w else 1.0, min_h / h if h < min_h else 1.0)

    if scale > 1.0:
        return cv2.resize(
            img,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC,
        )

    return img


def _resize_width(img: np.ndarray, min_width: int) -> np.ndarray:
    h, w = img.shape[:2]
    if w <= 0:
        return img

    if w < min_width:
        scale = min_width / w
        return cv2.resize(
            img,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC,
        )

    return img


def _black_on_white(gray: np.ndarray) -> np.ndarray:
    if np.mean(gray) < 127:
        return cv2.bitwise_not(gray)
    return gray


def _blue_mask(image: np.ndarray) -> np.ndarray:
    bgr = _ensure_bgr(image)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    blue_1 = cv2.inRange(
        hsv,
        np.array([85, 25, 25], np.uint8),
        np.array([145, 255, 255], np.uint8),
    )

    blue_2 = cv2.inRange(
        hsv,
        np.array([95, 35, 15], np.uint8),
        np.array([165, 255, 170], np.uint8),
    )

    mask = cv2.bitwise_or(blue_1, blue_2)
    mask = cv2.medianBlur(mask, 3)
    mask = cv2.dilate(mask, np.ones((2, 2), np.uint8), iterations=1)

    return mask


def _dark_mask(image: np.ndarray) -> np.ndarray:
    gray = _to_gray(image)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    enhanced = _clahe(gray, clip=2.5, tile=8)

    otsu = cv2.threshold(
        enhanced,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )[1]

    adaptive = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        9,
    )

    mask = cv2.bitwise_or(otsu, adaptive)
    mask = cv2.medianBlur(mask, 3)

    return mask


def _remove_grid_lines(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape[:2]

    if h < 8 or w < 8:
        return mask

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, max(8, int(h * 0.55))),
    )
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(8, int(w * 0.55)), 1),
    )

    vertical = cv2.morphologyEx(mask, cv2.MORPH_OPEN, vertical_kernel)
    horizontal = cv2.morphologyEx(mask, cv2.MORPH_OPEN, horizontal_kernel)
    lines = cv2.bitwise_or(vertical, horizontal)

    cleaned = cv2.subtract(mask, lines)
    cleaned = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_OPEN,
        np.ones((2, 2), np.uint8),
        iterations=1,
    )

    return cleaned


def _mask_to_digit_image(mask: np.ndarray) -> np.ndarray | None:
    h, w = mask.shape[:2]

    if h <= 0 or w <= 0:
        return None

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes: list[tuple[int, int, int, int]] = []
    area_img = h * w

    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)

        if area < max(4, area_img * 0.002):
            continue
        if bw < max(2, int(w * 0.03)):
            continue
        if bh < max(5, int(h * 0.12)):
            continue
        if bw > int(w * 0.95) and bh > int(h * 0.85):
            continue

        boxes.append((x, y, bw, bh))

    if not boxes:
        return None

    x1 = min(x for x, _, _, _ in boxes)
    y1 = min(y for _, y, _, _ in boxes)
    x2 = max(x + bw for x, _, bw, _ in boxes)
    y2 = max(y + bh for _, y, _, bh in boxes)

    pad_x = max(2, int((x2 - x1) * 0.20))
    pad_y = max(2, int((y2 - y1) * 0.20))

    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)

    digit_mask = mask[y1:y2, x1:x2]

    if digit_mask.size == 0:
        return None

    digit_img = np.full_like(digit_mask, 255)
    digit_img[digit_mask > 0] = 0

    digit_img = _resize_min(digit_img, min_w=120, min_h=120)
    digit_img = _pad_white(digit_img, pad=24)

    return digit_img


def _prepare_original_digit(cell: np.ndarray) -> np.ndarray:
    gray = _to_gray(cell)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    gray = _clahe(gray, clip=2.5, tile=4)
    gray = _black_on_white(gray)
    gray = _resize_min(gray, min_w=120, min_h=120)
    gray = _pad_white(gray, pad=24)
    return gray


def _cluster_positions(values: np.ndarray, threshold: float, min_gap: int = 2) -> list[tuple[int, int]]:
    clusters: list[tuple[int, int]] = []
    start: int | None = None

    for i, value in enumerate(values):
        if value >= threshold:
            if start is None:
                start = i
        else:
            if start is not None:
                if i - start >= min_gap:
                    clusters.append((start, i - 1))
                start = None

    if start is not None and len(values) - start >= min_gap:
        clusters.append((start, len(values) - 1))

    return clusters


def _detect_vertical_line_clusters(crop: np.ndarray) -> list[tuple[int, int, int]]:
    gray = _to_gray(crop)
    h, w = gray.shape[:2]

    if h < 10 or w < 10:
        return []

    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    binary = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        8,
    )

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, max(8, int(h * 0.45))),
    )

    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

    projection = np.sum(vertical > 0, axis=0).astype(np.float32)
    threshold = max(3.0, h * 0.20)

    raw_clusters = _cluster_positions(projection, threshold, min_gap=1)

    clusters: list[tuple[int, int, int]] = []

    for x1, x2 in raw_clusters:
        if x2 - x1 > max(2, int(w * 0.08)):
            continue

        center = int(round((x1 + x2) / 2))
        clusters.append((x1, x2, center))

    merged: list[tuple[int, int, int]] = []

    for cluster in clusters:
        if not merged:
            merged.append(cluster)
            continue

        prev = merged[-1]
        if cluster[0] - prev[1] <= max(2, int(w * 0.015)):
            x1 = prev[0]
            x2 = cluster[1]
            center = int(round((x1 + x2) / 2))
            merged[-1] = (x1, x2, center)
        else:
            merged.append(cluster)

    return merged


def _choose_cell_sequence(
    clusters: list[tuple[int, int, int]],
    expected_digits: int,
    width: int,
) -> list[tuple[int, int, int]] | None:
    needed = expected_digits + 1

    if len(clusters) < needed:
        return None

    best_seq: list[tuple[int, int, int]] | None = None
    best_score = float("-inf")

    for i in range(0, len(clusters) - needed + 1):
        seq = clusters[i:i + needed]
        centers = [c[2] for c in seq]
        gaps = np.diff(centers)

        if len(gaps) != expected_digits:
            continue

        if np.any(gaps <= 3):
            continue

        mean_gap = float(np.mean(gaps))
        std_gap = float(np.std(gaps))
        coverage = centers[-1] - centers[0]

        if mean_gap <= 0:
            continue

        uniformity = 1.0 - min(1.0, std_gap / mean_gap)
        coverage_score = min(1.0, coverage / max(1, width))
        margin_penalty = abs((centers[0] + centers[-1]) / 2 - width / 2) / max(1, width)

        score = uniformity * 2.0 + coverage_score - margin_penalty

        if score > best_score:
            best_score = score
            best_seq = seq

    return best_seq


def _cells_from_detected_grid(crop: np.ndarray, expected_digits: int) -> list[np.ndarray]:
    h, w = crop.shape[:2]

    clusters = _detect_vertical_line_clusters(crop)
    sequence = _choose_cell_sequence(clusters, expected_digits, w)

    if sequence is None:
        return []

    cells: list[np.ndarray] = []

    for i in range(expected_digits):
        left_line = sequence[i]
        right_line = sequence[i + 1]

        x1 = min(w - 1, left_line[1] + 1)
        x2 = max(0, right_line[0] - 1)

        if x2 <= x1:
            x1 = min(w - 1, left_line[2] + 1)
            x2 = max(0, right_line[2] - 1)

        if x2 <= x1:
            continue

        y_margin = max(1, int(h * 0.08))
        cell = crop[y_margin:h - y_margin, x1:x2]

        if cell.size > 0:
            cells.append(cell)

    if len(cells) == expected_digits:
        return cells

    return []


def _cells_by_equal_split(crop: np.ndarray, expected_digits: int) -> list[np.ndarray]:
    h, w = crop.shape[:2]

    if expected_digits <= 0 or h <= 0 or w <= 0:
        return []

    cells: list[np.ndarray] = []

    for i in range(expected_digits):
        x1 = round(i * w / expected_digits)
        x2 = round((i + 1) * w / expected_digits)

        margin_x = max(1, int((x2 - x1) * 0.12))
        margin_y = max(1, int(h * 0.12))

        cx1 = min(w, x1 + margin_x)
        cx2 = max(0, x2 - margin_x)
        cy1 = min(h, margin_y)
        cy2 = max(0, h - margin_y)

        if cx2 <= cx1 or cy2 <= cy1:
            cell = crop[:, x1:x2]
        else:
            cell = crop[cy1:cy2, cx1:cx2]

        if cell.size > 0:
            cells.append(cell)

    return cells


def _cells_by_ink_projection(crop: np.ndarray, expected_digits: int, field_type: str) -> list[np.ndarray]:
    if expected_digits <= 0:
        return []

    bgr = _ensure_bgr(crop)

    if field_type == "handwritten_number":
        mask = _blue_mask(bgr)
    else:
        mask = _remove_grid_lines(_dark_mask(bgr))

    h, w = mask.shape[:2]

    if h <= 0 or w <= 0:
        return []

    projection = np.sum(mask > 0, axis=0).astype(np.float32)
    threshold = max(1.0, np.max(projection) * 0.12) if np.max(projection) > 0 else 1.0
    clusters = _cluster_positions(projection, threshold, min_gap=max(1, int(w * 0.01)))

    boxes: list[tuple[int, int]] = []

    for x1, x2 in clusters:
        if x2 - x1 < max(2, int(w * 0.02)):
            continue
        if x2 - x1 > int(w * 0.70):
            continue
        boxes.append((x1, x2))

    if len(boxes) != expected_digits:
        return []

    cells: list[np.ndarray] = []

    for x1, x2 in boxes:
        pad_x = max(2, int((x2 - x1) * 0.45))
        xx1 = max(0, x1 - pad_x)
        xx2 = min(w, x2 + pad_x)
        cell = crop[:, xx1:xx2]

        if cell.size > 0:
            cells.append(cell)

    return cells


def _candidate_cell_sets(
    crop: np.ndarray,
    expected_digits: int,
    field_type: str,
) -> list[tuple[str, list[np.ndarray]]]:
    candidates: list[tuple[str, list[np.ndarray]]] = []

    grid_cells = _cells_from_detected_grid(crop, expected_digits)
    if len(grid_cells) == expected_digits:
        candidates.append(("grid_cells", grid_cells))

    ink_cells = _cells_by_ink_projection(crop, expected_digits, field_type)
    if len(ink_cells) == expected_digits:
        candidates.append(("ink_projection", ink_cells))

    equal_cells = _cells_by_equal_split(crop, expected_digits)
    if len(equal_cells) == expected_digits:
        candidates.append(("equal_split", equal_cells))

    return candidates


def _digit_image_variants(cell: np.ndarray, field_type: str) -> list[tuple[str, np.ndarray]]:
    bgr = _ensure_bgr(cell)
    variants: list[tuple[str, np.ndarray]] = []

    if field_type == "handwritten_number":
        blue = _blue_mask(bgr)
        blue = _remove_grid_lines(blue)
        blue_digit = _mask_to_digit_image(blue)

        if blue_digit is not None:
            variants.append(("blue_content", blue_digit))

        dark = _remove_grid_lines(_dark_mask(bgr))
        dark_digit = _mask_to_digit_image(dark)

        if dark_digit is not None:
            variants.append(("dark_content", dark_digit))

    else:
        dark = _remove_grid_lines(_dark_mask(bgr))
        dark_digit = _mask_to_digit_image(dark)

        if dark_digit is not None:
            variants.append(("dark_content", dark_digit))

        blue = _blue_mask(bgr)
        blue_digit = _mask_to_digit_image(blue)

        if blue_digit is not None:
            variants.append(("blue_content", blue_digit))

    variants.append(("original_enhanced", _prepare_original_digit(bgr)))

    return variants


def _run_tesseract(
    processed: np.ndarray,
    config: str,
    lang: str,
) -> tuple[str, float]:
    if not _TESSERACT_OK:
        return "", 0.0

    try:
        data = pytesseract.image_to_data(
            processed,
            config=config,
            lang=lang,
            output_type=pytesseract.Output.DICT,
        )

        words: list[str] = []
        confs: list[float] = []

        for text, conf in zip(data.get("text", []), data.get("conf", [])):
            text = str(text).strip()
            cf = _safe_conf(conf)

            if text and cf >= 0:
                words.append(text)
                confs.append(cf)

        raw = " ".join(words).strip()

        if not raw:
            raw = pytesseract.image_to_string(
                processed,
                config=config,
                lang=lang,
            ).strip()

        if confs:
            confidence = round(sum(confs) / len(confs) / 100.0, 3)
        else:
            confidence = 0.20 if raw else 0.0

        return raw, confidence

    except Exception:
        return "", 0.0


def _read_single_digit(cell: np.ndarray, field_type: str) -> tuple[str, str, float, str] | None:
    variants = _digit_image_variants(cell, field_type)

    best_digit: str | None = None
    best_raw = ""
    best_conf = -1.0
    best_strategy = ""

    for variant_name, image in variants:
        for psm in (10, 13, 8):
            raw, conf = _run_tesseract(image, _digit_cfg(psm), _DIGIT_LANG)
            digits = _correct_digits(raw)

            if not digits:
                continue

            digit = digits[0]
            adjusted_conf = conf

            if len(digits) == 1:
                adjusted_conf += 0.08
            else:
                adjusted_conf -= min(0.25, 0.08 * (len(digits) - 1))

            if variant_name in ("blue_content", "dark_content"):
                adjusted_conf += 0.06

            adjusted_conf = max(0.0, min(1.0, adjusted_conf))

            if adjusted_conf > best_conf:
                best_digit = digit
                best_raw = raw
                best_conf = adjusted_conf
                best_strategy = f"{variant_name}/psm{psm}"

    if best_digit is None:
        return None

    return best_digit, best_raw, round(best_conf, 3), best_strategy


def _score_boxed_candidate(
    value: str,
    confidence: float,
    cell_set_name: str,
) -> float:
    score = confidence

    if cell_set_name == "grid_cells":
        score += 0.12
    elif cell_set_name == "ink_projection":
        score += 0.08
    elif cell_set_name == "equal_split":
        score -= 0.03

    if len(set(value)) == 1 and len(value) >= 3:
        score -= 0.12

    return score


def _ocr_boxed_digits(
    crop: np.ndarray,
    field_type: str,
    expected_digits: int,
) -> FieldOCRResult | None:
    if expected_digits <= 0 or expected_digits > 4:
        return None

    bgr = _ensure_bgr(crop)
    cell_sets = _candidate_cell_sets(bgr, expected_digits, field_type)

    best: FieldOCRResult | None = None
    best_score = float("-inf")

    for cell_set_name, cells in cell_sets:
        digits: list[str] = []
        raw_parts: list[str] = []
        confs: list[float] = []
        strategies: list[str] = []

        failed = False

        for cell in cells:
            result = _read_single_digit(cell, field_type)

            if result is None:
                failed = True
                break

            digit, raw, conf, strategy = result
            digits.append(digit)
            raw_parts.append(raw)
            confs.append(conf)
            strategies.append(strategy)

        if failed or len(digits) != expected_digits:
            continue

        value = "".join(digits)
        confidence = round(sum(confs) / len(confs), 3) if confs else 0.0
        candidate_score = _score_boxed_candidate(value, confidence, cell_set_name)

        candidate = FieldOCRResult(
            value=value,
            raw_text=" | ".join(raw_parts),
            confidence=confidence,
            status=_status_from(value, confidence),
            strategy=f"{cell_set_name}:" + ",".join(strategies),
        )

        if candidate_score > best_score:
            best = candidate
            best_score = candidate_score

    return best


def _normalize_numeric_value(digits: str, expected_digits: int | None) -> str | None:
    if not digits:
        return None

    if expected_digits is None:
        return digits

    if len(digits) == expected_digits:
        return digits

    if expected_digits <= 4 and len(digits) == expected_digits - 1:
        return digits.zfill(expected_digits)

    return None


def _number_block_variants(crop: np.ndarray, field_type: str) -> list[tuple[str, np.ndarray]]:
    bgr = _ensure_bgr(crop)
    gray = _to_gray(bgr)

    variants: list[tuple[str, np.ndarray]] = []

    if field_type == "handwritten_number":
        blue = _blue_mask(bgr)
        blue = _remove_grid_lines(blue)
        blue_img = _mask_to_digit_image(blue)

        if blue_img is not None:
            variants.append(("block_blue_content", blue_img))

        dark = _remove_grid_lines(_dark_mask(bgr))
        dark_img = _mask_to_digit_image(dark)

        if dark_img is not None:
            variants.append(("block_dark_content", dark_img))

    else:
        dark = _remove_grid_lines(_dark_mask(bgr))
        dark_img = _mask_to_digit_image(dark)

        if dark_img is not None:
            variants.append(("block_dark_content", dark_img))

    enhanced = _clahe(gray, clip=2.5, tile=8)
    enhanced = _black_on_white(enhanced)
    enhanced = _resize_width(enhanced, min_width=320)
    enhanced = _pad_white(enhanced, pad=18)

    variants.append(("block_clahe", enhanced))

    otsu = cv2.threshold(
        enhanced,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]
    variants.append(("block_otsu", otsu))

    adaptive = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        9,
    )
    variants.append(("block_adaptive", adaptive))

    return variants


def _select_numeric_psms(expected_digits: int | None) -> tuple[int, ...]:
    if expected_digits is None:
        return (7, 8, 13)
    if expected_digits == 1:
        return (10, 13, 8)
    if expected_digits <= 4:
        return (8, 7, 13)
    return (7, 13, 8, 6)


def _ocr_number_block(
    crop: np.ndarray,
    field_type: str,
    expected_digits: int | None,
) -> FieldOCRResult:
    variants = _number_block_variants(crop, field_type)
    psms = _select_numeric_psms(expected_digits)

    best_valid: FieldOCRResult | None = None
    best_rejected: FieldOCRResult | None = None
    best_empty: FieldOCRResult | None = None

    for variant_name, image in variants:
        for psm in psms:
            raw, conf = _run_tesseract(image, _digit_cfg(psm), _DIGIT_LANG)
            digits = _correct_digits(raw)
            value = _normalize_numeric_value(digits, expected_digits)

            strategy = f"{variant_name}/psm{psm}"

            if value is not None:
                result = FieldOCRResult(
                    value=value,
                    raw_text=raw,
                    confidence=conf,
                    status=_status_from(value, conf),
                    strategy=strategy,
                )

                if best_valid is None or result.confidence > best_valid.confidence:
                    best_valid = result

            elif digits:
                result = FieldOCRResult(
                    value=None,
                    raw_text=raw,
                    confidence=conf,
                    status="BAJA_CONFIANZA",
                    strategy=f"{strategy}:rejected_len_{len(digits)}",
                )

                if best_rejected is None or result.confidence > best_rejected.confidence:
                    best_rejected = result

            else:
                result = FieldOCRResult(
                    value=None,
                    raw_text=raw,
                    confidence=conf,
                    status="CAMPO_VACIO",
                    strategy=strategy,
                )

                if best_empty is None or result.confidence > best_empty.confidence:
                    best_empty = result

    if best_valid is not None:
        return best_valid

    if best_rejected is not None:
        return best_rejected

    if best_empty is not None:
        return best_empty

    return _EMPTY


def _text_variants(crop: np.ndarray) -> list[tuple[str, np.ndarray]]:
    bgr = _ensure_bgr(crop)
    gray = _to_gray(bgr)

    variants: list[tuple[str, np.ndarray]] = []

    enhanced = _clahe(gray, clip=2.2, tile=8)
    enhanced = _black_on_white(enhanced)
    enhanced = _resize_width(enhanced, min_width=420)
    enhanced = _pad_white(enhanced, pad=16)

    variants.append(("text_clahe", enhanced))

    adaptive = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        9,
    )
    variants.append(("text_adaptive", adaptive))

    otsu = cv2.threshold(
        enhanced,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]
    variants.append(("text_otsu", otsu))

    return variants


def _ocr_text_block(crop: np.ndarray) -> FieldOCRResult:
    variants = _text_variants(crop)

    best: FieldOCRResult | None = None

    for variant_name, image in variants:
        for psm in (7, 6, 11):
            raw, conf = _run_tesseract(image, _text_cfg(psm), _TEXT_LANG)
            value = _clean_text(raw) or None

            if value is not None and len(value) <= 1 and conf < 0.40:
                value = None

            result = FieldOCRResult(
                value=value,
                raw_text=raw,
                confidence=conf,
                status=_status_from(value, conf),
                strategy=f"{variant_name}/psm{psm}",
            )

            if best is None:
                best = result
                continue

            current_score = result.confidence + (0.05 if result.value else 0.0)
            best_score = best.confidence + (0.05 if best.value else 0.0)

            if current_score > best_score:
                best = result

    return best if best is not None else _EMPTY


def ocr_field(
    crop: np.ndarray,
    field_type: str,
    expected_digits: int | None = None,
) -> FieldOCRResult:
    if not _TESSERACT_OK:
        return _NO_TESSERACT

    if crop is None or crop.size == 0:
        return _EMPTY

    is_number = field_type in ("handwritten_number", "printed_number")

    if is_number and expected_digits is not None and 1 <= expected_digits <= 4:
        boxed = _ocr_boxed_digits(crop, field_type, expected_digits)
        block = _ocr_number_block(crop, field_type, expected_digits)

        if boxed is not None and boxed.value is not None:
            if block.value is not None and block.confidence > boxed.confidence + 0.25:
                return block
            return boxed

        return block

    if is_number:
        return _ocr_number_block(crop, field_type, expected_digits)

    return _ocr_text_block(crop)


def parse_time(text: str) -> tuple[int | None, int | None]:
    digits = re.sub(r"[^\d]", "", text)

    if len(digits) == 4:
        h, m = int(digits[:2]), int(digits[2:])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m

    if len(digits) == 3:
        h, m = int(digits[0]), int(digits[1:])
        if 0 <= h <= 9 and 0 <= m <= 59:
            return h, m

    return None, None
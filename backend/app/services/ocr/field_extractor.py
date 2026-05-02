from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[4]

DEFAULT_INPUT_DIR = PROJECT_ROOT / "samples" / "actas" / "converted"
DEFAULT_DEBUG_DIR = PROJECT_ROOT / "samples" / "actas" / "fields_debug"

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}

STANDARD_WIDTH = 2048
STANDARD_HEIGHT = 1339

_DARK_THRESHOLD_ALTA = 0.55
_DARK_THRESHOLD_MEDIA = 0.30


@dataclass(frozen=True)
class FieldRegion:
    name: str
    x1: float
    y1: float
    x2: float
    y2: float
    required: bool = True
    field_type: str = "number"
    expected_digits: int | None = None


@dataclass
class FieldCropResult:
    name: str
    required: bool
    field_type: str
    expected_digits: int | None
    obstruction_level: str
    dark_ratio: float
    blue_ratio: float
    light_ratio: float
    status: str
    coordinates: dict
    crop_path: str | None = None
    digit_crop_paths: list[str] | None = None


@dataclass
class NormalizationResult:
    image: np.ndarray
    rotation_applied: int
    orientation_status: str
    skew_angle: float
    external_margin_cropped: bool
    normalization_mode: str


FIELD_REGIONS: tuple[FieldRegion, ...] = (
    FieldRegion("mesa_codigo", 0.055, 0.165, 0.185, 0.230, True, "printed_number", 13),

    FieldRegion("departamento", 0.240, 0.163, 0.390, 0.180, False, "printed_text"),
    FieldRegion("provincia", 0.240, 0.180, 0.390, 0.193, False, "printed_text"),
    FieldRegion("municipio", 0.240, 0.193, 0.390, 0.207, False, "printed_text"),
    FieldRegion("recinto_nombre", 0.240, 0.207, 0.455, 0.222, False, "printed_text"),
    FieldRegion("recinto_direccion", 0.240, 0.222, 0.640, 0.252, False, "printed_text"),

    FieldRegion("nro_mesa", 0.060, 0.330, 0.155, 0.455, True, "printed_number", 1),

    FieldRegion("apertura_time", 0.060, 0.505, 0.165, 0.555, False, "handwritten_number", 4),
    FieldRegion("apertura_hora", 0.060, 0.505, 0.105, 0.555, False, "handwritten_number", 2),
    FieldRegion("apertura_minutos", 0.108, 0.505, 0.165, 0.555, False, "handwritten_number", 2),

    FieldRegion("cierre_time", 0.060, 0.645, 0.165, 0.695, False, "handwritten_number", 4),
    FieldRegion("cierre_hora", 0.060, 0.645, 0.105, 0.695, False, "handwritten_number", 2),
    FieldRegion("cierre_minutos", 0.108, 0.645, 0.165, 0.695, False, "handwritten_number", 2),

    FieldRegion("nro_votantes", 0.062, 0.725, 0.155, 0.770, True, "printed_number", 3),
    FieldRegion("total_boletas", 0.075, 0.805, 0.165, 0.855, True, "handwritten_number", 3),
    FieldRegion("boletas_no_utilizadas", 0.075, 0.895, 0.165, 0.950, False, "handwritten_number", 3),

    FieldRegion("partido_1_votos", 0.328, 0.288, 0.392, 0.330, True, "handwritten_number", 3),
    FieldRegion("partido_2_votos", 0.328, 0.330, 0.392, 0.372, True, "handwritten_number", 3),
    FieldRegion("partido_3_votos", 0.328, 0.370, 0.392, 0.412, True, "handwritten_number", 3),
    FieldRegion("partido_4_votos", 0.328, 0.410, 0.392, 0.455, True, "handwritten_number", 3),

    FieldRegion("votos_validos", 0.328, 0.655, 0.392, 0.700, True, "handwritten_number", 3),
    FieldRegion("votos_blancos", 0.328, 0.733, 0.392, 0.765, True, "handwritten_number", 3),
    FieldRegion("votos_nulos", 0.328, 0.765, 0.392, 0.810, True, "handwritten_number", 3),

    FieldRegion("observaciones", 0.160, 0.835, 0.645, 0.935, False, "printed_text"),
)


_REGION_COLORS: dict[str, tuple[int, int, int]] = {
    "printed_number": (0, 180, 0),
    "handwritten_number": (0, 140, 255),
    "printed_text": (180, 0, 180),
}

_OBSTRUCTED_COLOR: tuple[int, int, int] = (0, 0, 210)
_WARNING_COLOR: tuple[int, int, int] = (0, 180, 255)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_image(image_path: Path) -> np.ndarray:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")
    return image


def save_image(image: np.ndarray, output_path: Path) -> str:
    ensure_directory(output_path.parent)
    if not cv2.imwrite(str(output_path), image):
        raise RuntimeError(f"No se pudo guardar: {output_path}")
    return str(output_path)


def resize_to_standard(image: np.ndarray) -> np.ndarray:
    return cv2.resize(
        image,
        (STANDARD_WIDTH, STANDARD_HEIGHT),
        interpolation=cv2.INTER_LANCZOS4,
    )


def crop_relative(
    image: np.ndarray,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> tuple[np.ndarray, dict]:
    h, w = image.shape[:2]

    left = max(0, min(w, int(round(w * x1))))
    top = max(0, min(h, int(round(h * y1))))
    right = max(0, min(w, int(round(w * x2))))
    bottom = max(0, min(h, int(round(h * y2))))

    if right <= left or bottom <= top:
        raise ValueError("La región de recorte es inválida.")

    coords = {"x1": left, "y1": top, "x2": right, "y2": bottom}
    return image[top:bottom, left:right], coords


def calculate_dark_ratio(image: np.ndarray, threshold: int = 55) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray < threshold))


def calculate_light_ratio(image: np.ndarray, threshold: int = 245) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray > threshold))


def calculate_blue_ratio(image: np.ndarray) -> float:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([85, 30, 30], dtype=np.uint8)
    upper_blue = np.array([150, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    return float(np.mean(mask > 0))


def calculate_vertical_edge_ratio(image: np.ndarray, threshold: int = 80) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    return float(np.mean(np.abs(sobel_x) > threshold))


def detect_obstruction_level(dark_ratio: float) -> str:
    if dark_ratio >= _DARK_THRESHOLD_ALTA:
        return "ALTA"
    if dark_ratio >= _DARK_THRESHOLD_MEDIA:
        return "MEDIA"
    return "BAJA"


def classify_field_status(
    region: FieldRegion,
    dark_ratio: float,
    blue_ratio: float,
    light_ratio: float,
) -> str:
    obstruction_level = detect_obstruction_level(dark_ratio)

    if obstruction_level == "ALTA":
        return "POSIBLE_OBSTRUCCION"

    if region.required and region.field_type in {"printed_number", "handwritten_number"}:
        if dark_ratio < 0.002 and blue_ratio < 0.002:
            return "POSIBLE_CAMPO_VACIO"

    if region.field_type == "handwritten_number":
        if light_ratio > 0.96 and dark_ratio < 0.010 and blue_ratio < 0.010:
            return "POSIBLE_CAMPO_BORROSO_O_VACIO"

    return "OK"


def rotate_image(image: np.ndarray, rotation: int) -> np.ndarray:
    if rotation == 0:
        return image
    if rotation == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if rotation == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if rotation == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(f"Rotación no soportada: {rotation}")


def score_orientation(image: np.ndarray) -> float:
    h, w = image.shape[:2]
    landscape_score = 3.0 if w > h else 0.0

    try:
        top_left_logo, _ = crop_relative(image, 0.025, 0.020, 0.180, 0.180)
        top_right_barcode, _ = crop_relative(image, 0.780, 0.020, 0.930, 0.180)
        vote_block, _ = crop_relative(image, 0.160, 0.250, 0.450, 0.570)
        left_column, _ = crop_relative(image, 0.030, 0.120, 0.190, 0.900)
    except ValueError:
        return 0.0

    return (
        landscape_score
        + 2.0 * calculate_dark_ratio(top_left_logo)
        + 3.0 * calculate_vertical_edge_ratio(top_right_barcode)
        + 2.0 * calculate_blue_ratio(vote_block)
        + 1.0 * calculate_dark_ratio(left_column)
    )


def normalize_orientation(image: np.ndarray) -> tuple[np.ndarray, int, str]:
    candidates = []

    for rotation in (0, 90, 180, 270):
        rotated = rotate_image(image, rotation)
        score = score_orientation(rotated)
        candidates.append((rotation, rotated, score))

    candidates.sort(key=lambda item: item[2], reverse=True)

    best_rotation, best_image, best_score = candidates[0]
    second_score = candidates[1][2]
    margin = best_score - second_score

    if best_rotation == 0:
        return best_image, 0, "OK"

    if margin < 0.020:
        return image, 0, "ORIENTACION_INCIERTA"

    return best_image, best_rotation, "CORREGIDA"


def estimate_skew_angle_hough(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    h, w = image.shape[:2]
    min_line_length = max(120, int(w * 0.20))

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=120,
        minLineLength=min_line_length,
        maxLineGap=25,
    )

    if lines is None:
        return 0.0

    angles: list[float] = []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0:
            continue

        angle = np.degrees(np.arctan2(dy, dx))

        if -8.0 <= angle <= 8.0:
            angles.append(float(angle))

    if not angles:
        return 0.0

    median_angle = float(np.median(angles))

    if abs(median_angle) > 8:
        return 0.0

    return round(median_angle, 3)


def rotate_same_size(image: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.05:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    return cv2.warpAffine(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def deskew_image(image: np.ndarray) -> tuple[np.ndarray, float]:
    angle = estimate_skew_angle_hough(image)

    if abs(angle) < 0.05:
        return image, 0.0

    corrected = rotate_same_size(image, angle * -1)
    return corrected, angle


def crop_external_black_margins(image: np.ndarray) -> tuple[np.ndarray, bool]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mask = gray > 18
    ys, xs = np.where(mask)

    if len(xs) < 1000:
        return image, False

    x1 = int(np.percentile(xs, 0.05))
    x2 = int(np.percentile(xs, 99.95))
    y1 = int(np.percentile(ys, 0.05))
    y2 = int(np.percentile(ys, 99.95))

    h, w = image.shape[:2]

    removed_left = x1
    removed_right = w - x2
    removed_top = y1
    removed_bottom = h - y2
    max_removed = max(removed_left, removed_right, removed_top, removed_bottom)

    if max_removed < min(w, h) * 0.02:
        return image, False

    crop_w = x2 - x1
    crop_h = y2 - y1

    if crop_w <= 0 or crop_h <= 0:
        return image, False

    aspect = crop_w / float(crop_h)

    if not (1.35 <= aspect <= 1.70):
        return image, False

    cropped = image[y1:y2, x1:x2]

    if cropped.size == 0:
        return image, False

    return cropped, True


def normalize_image_result(image: np.ndarray) -> NormalizationResult:
    oriented, rotation_applied, orientation_status = normalize_orientation(image)
    no_margin, margin_cropped = crop_external_black_margins(oriented)
    deskewed, skew_angle = deskew_image(no_margin)
    standardized = resize_to_standard(deskewed)

    mode = "full_page_template"

    if margin_cropped:
        mode = "external_margin_crop_then_template"

    return NormalizationResult(
        image=standardized,
        rotation_applied=rotation_applied,
        orientation_status=orientation_status,
        skew_angle=skew_angle,
        external_margin_cropped=margin_cropped,
        normalization_mode=mode,
    )


def normalize_image(image: np.ndarray) -> tuple[np.ndarray, int, str, bool, float]:
    result = normalize_image_result(image)
    return (
        result.image,
        result.rotation_applied,
        result.orientation_status,
        result.external_margin_cropped,
        result.skew_angle,
    )


def _blue_digit_mask(crop: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    blue_1 = cv2.inRange(
        hsv,
        np.array([85, 25, 25], np.uint8),
        np.array([150, 255, 255], np.uint8),
    )

    blue_2 = cv2.inRange(
        hsv,
        np.array([95, 35, 15], np.uint8),
        np.array([170, 255, 170], np.uint8),
    )

    mask = cv2.bitwise_or(blue_1, blue_2)
    mask = cv2.medianBlur(mask, 3)
    mask = cv2.dilate(mask, np.ones((2, 2), np.uint8), iterations=1)

    return mask


def _dark_digit_mask(crop: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    enhanced = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)

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


def _line_mask(crop: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    binary = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        8,
    )

    h, w = binary.shape[:2]

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, max(8, int(h * 0.45))),
    )

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(8, int(w * 0.45)), 1),
    )

    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

    return cv2.bitwise_or(vertical, horizontal)


def _remove_lines(mask: np.ndarray, crop: np.ndarray) -> np.ndarray:
    lines = _line_mask(crop)
    cleaned = cv2.subtract(mask, lines)

    cleaned = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_OPEN,
        np.ones((2, 2), np.uint8),
        iterations=1,
    )

    cleaned = cv2.dilate(cleaned, np.ones((2, 2), np.uint8), iterations=1)

    return cleaned


def _digit_content_mask(crop: np.ndarray, field_type: str) -> np.ndarray:
    blue = _blue_digit_mask(crop)
    dark = _dark_digit_mask(crop)

    blue_ratio = float(np.mean(blue > 0))

    if field_type == "handwritten_number" and blue_ratio > 0.003:
        mask = blue
    else:
        mask = dark

    return _remove_lines(mask, crop)


def _cluster_projection(
    projection: np.ndarray,
    threshold: float,
    min_width: int,
) -> list[tuple[int, int]]:
    clusters: list[tuple[int, int]] = []
    start: int | None = None

    for index, value in enumerate(projection):
        if value >= threshold:
            if start is None:
                start = index
        else:
            if start is not None:
                end = index - 1
                if end - start + 1 >= min_width:
                    clusters.append((start, end))
                start = None

    if start is not None:
        end = len(projection) - 1
        if end - start + 1 >= min_width:
            clusters.append((start, end))

    return clusters


def _merge_close_clusters(
    clusters: list[tuple[int, int]],
    max_gap: int,
) -> list[tuple[int, int]]:
    if not clusters:
        return []

    merged: list[tuple[int, int]] = [clusters[0]]

    for start, end in clusters[1:]:
        last_start, last_end = merged[-1]

        if start - last_end <= max_gap:
            merged[-1] = (last_start, end)
        else:
            merged.append((start, end))

    return merged


def _detect_vertical_grid_lines(crop: np.ndarray) -> list[int]:
    lines = _line_mask(crop)
    h, w = lines.shape[:2]

    projection = np.sum(lines > 0, axis=0).astype(np.float32)
    threshold = max(3.0, h * 0.18)

    clusters = _cluster_projection(
        projection=projection,
        threshold=threshold,
        min_width=1,
    )

    centers: list[int] = []

    for start, end in clusters:
        if end - start > max(4, int(w * 0.08)):
            continue

        centers.append(int(round((start + end) / 2)))

    centers = sorted(centers)

    merged: list[int] = []

    for center in centers:
        if not merged:
            merged.append(center)
            continue

        if center - merged[-1] <= max(2, int(w * 0.015)):
            merged[-1] = int(round((merged[-1] + center) / 2))
        else:
            merged.append(center)

    return merged


def _score_grid_sequence(
    crop: np.ndarray,
    field_type: str,
    sequence: list[int],
    expected_digits: int,
) -> float:
    h, w = crop.shape[:2]
    gaps = np.diff(sequence)

    if len(gaps) != expected_digits:
        return -999.0

    if np.any(gaps <= 3):
        return -999.0

    mean_gap = float(np.mean(gaps))
    std_gap = float(np.std(gaps))

    if mean_gap <= 0:
        return -999.0

    content_mask = _digit_content_mask(crop, field_type)

    densities: list[float] = []

    for index in range(expected_digits):
        x1 = sequence[index]
        x2 = sequence[index + 1]

        margin_x = max(1, int((x2 - x1) * 0.10))
        margin_y = max(1, int(h * 0.10))

        left = max(0, min(w, x1 + margin_x))
        right = max(0, min(w, x2 - margin_x))
        top = max(0, min(h, margin_y))
        bottom = max(0, min(h, h - margin_y))

        if right <= left or bottom <= top:
            densities.append(0.0)
            continue

        cell_mask = content_mask[top:bottom, left:right]
        densities.append(float(np.mean(cell_mask > 0)))

    avg_density = float(np.mean(densities)) if densities else 0.0
    min_density = float(np.min(densities)) if densities else 0.0

    uniformity = 1.0 - min(1.0, std_gap / mean_gap)
    coverage = (sequence[-1] - sequence[0]) / max(1, w)
    center = (sequence[0] + sequence[-1]) / 2
    center_penalty = abs(center - (w / 2)) / max(1, w)

    edge_penalty = 0.0

    if sequence[0] <= max(2, int(w * 0.02)):
        edge_penalty += 0.15

    if sequence[-1] >= w - max(2, int(w * 0.02)):
        edge_penalty += 0.05

    density_score = min(1.0, avg_density * 60.0)
    min_density_score = min(1.0, min_density * 80.0)

    return (
        uniformity * 0.34
        + coverage * 0.16
        + density_score * 0.34
        + min_density_score * 0.16
        - center_penalty * 0.20
        - edge_penalty
    )


def _choose_grid_sequence(
    crop: np.ndarray,
    field_type: str,
    centers: list[int],
    expected_digits: int,
) -> list[int] | None:
    needed = expected_digits + 1
    h, w = crop.shape[:2]

    if len(centers) < needed:
        return None

    candidates = centers[:]
    best_sequence: list[int] | None = None
    best_score = -999.0

    for start in range(0, len(candidates) - needed + 1):
        sequence = candidates[start:start + needed]
        score = _score_grid_sequence(crop, field_type, sequence, expected_digits)

        if score > best_score:
            best_score = score
            best_sequence = sequence

    if best_sequence is None or best_score < 0.20:
        return None

    return best_sequence


def _split_by_detected_grid(
    crop: np.ndarray,
    expected_digits: int,
    field_type: str,
) -> list[np.ndarray]:
    h, w = crop.shape[:2]

    centers = _detect_vertical_grid_lines(crop)
    sequence = _choose_grid_sequence(crop, field_type, centers, expected_digits)

    if sequence is None:
        return []

    digit_crops: list[np.ndarray] = []

    for index in range(expected_digits):
        x1 = sequence[index]
        x2 = sequence[index + 1]

        margin_x = max(1, int((x2 - x1) * 0.08))
        margin_y = max(1, int(h * 0.10))

        left = max(0, min(w, x1 + margin_x))
        right = max(0, min(w, x2 - margin_x))
        top = max(0, min(h, margin_y))
        bottom = max(0, min(h, h - margin_y))

        if right <= left or bottom <= top:
            continue

        digit = crop[top:bottom, left:right]

        if digit.size > 0:
            digit_crops.append(digit)

    if len(digit_crops) == expected_digits:
        return digit_crops

    return []


def _bbox_from_mask(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask > 0)

    if len(xs) < 8:
        return None

    x1 = int(np.percentile(xs, 1))
    x2 = int(np.percentile(xs, 99))
    y1 = int(np.percentile(ys, 1))
    y2 = int(np.percentile(ys, 99))

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2


def _grid_bbox(crop: np.ndarray) -> tuple[int, int, int, int] | None:
    line_mask = _line_mask(crop)
    bbox = _bbox_from_mask(line_mask)

    if bbox is None:
        return None

    h, w = crop.shape[:2]
    x1, y1, x2, y2 = bbox

    if x2 - x1 < w * 0.25:
        return None

    if y2 - y1 < h * 0.25:
        return None

    return x1, y1, x2, y2


def _content_bbox(
    crop: np.ndarray,
    field_type: str,
) -> tuple[int, int, int, int] | None:
    mask = _digit_content_mask(crop, field_type)
    bbox = _bbox_from_mask(mask)

    if bbox is None:
        return None

    h, w = crop.shape[:2]
    x1, y1, x2, y2 = bbox

    pad_x = max(2, int((x2 - x1) * 0.35))
    pad_y = max(2, int((y2 - y1) * 0.35))

    return (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(w, x2 + pad_x),
        min(h, y2 + pad_y),
    )


def _split_by_trimmed_equal_width(
    crop: np.ndarray,
    expected_digits: int,
    field_type: str,
) -> list[np.ndarray]:
    h, w = crop.shape[:2]

    bbox = _grid_bbox(crop)

    if bbox is None:
        bbox = _content_bbox(crop, field_type)

    if bbox is None:
        trimmed = crop
    else:
        x1, y1, x2, y2 = bbox

        pad_x = max(1, int((x2 - x1) * 0.03))
        pad_y = max(1, int((y2 - y1) * 0.04))

        x1 = max(0, x1 - pad_x)
        x2 = min(w, x2 + pad_x)
        y1 = max(0, y1 - pad_y)
        y2 = min(h, y2 + pad_y)

        trimmed = crop[y1:y2, x1:x2]

    th, tw = trimmed.shape[:2]

    if th <= 0 or tw <= 0:
        return []

    digit_width = tw / expected_digits
    digit_crops: list[np.ndarray] = []

    for index in range(expected_digits):
        x1 = int(round(index * digit_width))
        x2 = int(round((index + 1) * digit_width))

        margin_x = max(1, int((x2 - x1) * 0.10))
        margin_y = max(1, int(th * 0.12))

        left = max(0, min(tw, x1 + margin_x))
        right = max(0, min(tw, x2 - margin_x))
        top = max(0, min(th, margin_y))
        bottom = max(0, min(th, th - margin_y))

        if right <= left or bottom <= top:
            digit = trimmed[:, x1:x2]
        else:
            digit = trimmed[top:bottom, left:right]

        if digit.size > 0:
            digit_crops.append(digit)

    return digit_crops


def _split_by_ink_projection(
    crop: np.ndarray,
    expected_digits: int,
    field_type: str,
) -> list[np.ndarray]:
    h, w = crop.shape[:2]
    mask = _digit_content_mask(crop, field_type)

    if float(np.mean(mask > 0)) < 0.001:
        return []

    projection = np.sum(mask > 0, axis=0).astype(np.float32)
    threshold = max(1.0, float(np.max(projection)) * 0.12)

    clusters = _cluster_projection(
        projection=projection,
        threshold=threshold,
        min_width=max(1, int(w * 0.008)),
    )

    clusters = _merge_close_clusters(clusters, max_gap=max(2, int(w * 0.035)))

    filtered: list[tuple[int, int]] = []

    for x1, x2 in clusters:
        width = x2 - x1 + 1

        if width < max(2, int(w * 0.015)):
            continue

        if width > int(w * 0.60):
            continue

        filtered.append((x1, x2))

    if len(filtered) != expected_digits:
        return []

    digit_crops: list[np.ndarray] = []

    for x1, x2 in filtered:
        pad_x = max(2, int((x2 - x1 + 1) * 0.70))
        left = max(0, x1 - pad_x)
        right = min(w, x2 + pad_x)

        digit = crop[:, left:right]

        if digit.size > 0:
            digit_crops.append(digit)

    return digit_crops


def split_digit_crops(
    crop: np.ndarray,
    expected_digits: int,
    field_type: str = "handwritten_number",
) -> list[np.ndarray]:
    if expected_digits <= 1:
        return [crop]

    grid_digits = _split_by_detected_grid(crop, expected_digits, field_type)

    if len(grid_digits) == expected_digits:
        return grid_digits

    ink_digits = _split_by_ink_projection(crop, expected_digits, field_type)

    if len(ink_digits) == expected_digits:
        return ink_digits

    trimmed_digits = _split_by_trimmed_equal_width(crop, expected_digits, field_type)

    if len(trimmed_digits) == expected_digits:
        return trimmed_digits

    h, w = crop.shape[:2]
    digit_width = w / expected_digits
    digit_crops: list[np.ndarray] = []

    for index in range(expected_digits):
        x1 = int(round(index * digit_width))
        x2 = int(round((index + 1) * digit_width))
        digit = crop[:, x1:x2]

        if digit.size > 0:
            digit_crops.append(digit)

    return digit_crops


def save_digit_crops(
    crop: np.ndarray,
    region: FieldRegion,
    acta_debug_dir: Path,
) -> list[str] | None:
    if region.expected_digits is None:
        return None

    digits_dir = acta_debug_dir / "digits" / region.name
    ensure_directory(digits_dir)

    digit_crops = split_digit_crops(
        crop=crop,
        expected_digits=region.expected_digits,
        field_type=region.field_type,
    )

    paths: list[str] = []

    for index, digit_crop in enumerate(digit_crops, start=1):
        digit_path = digits_dir / f"{index:02d}.png"
        paths.append(save_image(digit_crop, digit_path))

    return paths


def draw_field_regions(image: np.ndarray, metadata: list[FieldCropResult]) -> np.ndarray:
    vis = image.copy()

    for field in metadata:
        c = field.coordinates

        if field.status == "POSIBLE_OBSTRUCCION":
            color = _OBSTRUCTED_COLOR
        elif field.status != "OK":
            color = _WARNING_COLOR
        else:
            color = _REGION_COLORS.get(field.field_type, (180, 0, 180))

        cv2.rectangle(vis, (c["x1"], c["y1"]), (c["x2"], c["y2"]), color, 2)

        cv2.putText(
            vis,
            field.name,
            (c["x1"], max(0, c["y1"] - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            color,
            1,
            cv2.LINE_AA,
        )

    return vis


def extract_field_crops(
    image_path: Path,
    debug: bool = False,
    debug_dir: Path = DEFAULT_DEBUG_DIR,
) -> dict:
    image_path = image_path.resolve()

    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato no soportado: {image_path}")

    original = load_image(image_path)
    normalization = normalize_image_result(original)
    normalized = normalization.image

    acta_debug_dir = debug_dir / image_path.stem
    fields: dict[str, np.ndarray] = {}
    metadata: list[FieldCropResult] = []

    if debug:
        ensure_directory(acta_debug_dir)
        save_image(original, acta_debug_dir / "_original.png")
        save_image(normalized, acta_debug_dir / "_normalized.png")

    for region in FIELD_REGIONS:
        crop, coords = crop_relative(
            normalized,
            region.x1,
            region.y1,
            region.x2,
            region.y2,
        )

        dark_ratio = calculate_dark_ratio(crop)
        blue_ratio = calculate_blue_ratio(crop)
        light_ratio = calculate_light_ratio(crop)

        obstruction_level = detect_obstruction_level(dark_ratio)
        status = classify_field_status(region, dark_ratio, blue_ratio, light_ratio)

        crop_path: str | None = None
        digit_crop_paths: list[str] | None = None

        if debug:
            crop_path = save_image(crop, acta_debug_dir / f"{region.name}.png")
            digit_crop_paths = save_digit_crops(crop, region, acta_debug_dir)

        fields[region.name] = crop

        metadata.append(
            FieldCropResult(
                name=region.name,
                required=region.required,
                field_type=region.field_type,
                expected_digits=region.expected_digits,
                obstruction_level=obstruction_level,
                dark_ratio=round(dark_ratio, 4),
                blue_ratio=round(blue_ratio, 4),
                light_ratio=round(light_ratio, 4),
                status=status,
                coordinates=coords,
                crop_path=crop_path,
                digit_crop_paths=digit_crop_paths,
            )
        )

    manifest = {
        "source_image": str(image_path),
        "rotation_applied": normalization.rotation_applied,
        "orientation_status": normalization.orientation_status,
        "external_margin_cropped": normalization.external_margin_cropped,
        "normalization_mode": normalization.normalization_mode,
        "skew_angle": normalization.skew_angle,
        "standard_width": STANDARD_WIDTH,
        "standard_height": STANDARD_HEIGHT,
        "fields": [asdict(item) for item in metadata],
    }

    if debug:
        (acta_debug_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        regions_image = draw_field_regions(normalized, metadata)
        save_image(regions_image, acta_debug_dir / "_regions.png")

    return {
        "source_image": str(image_path),
        "rotation_applied": normalization.rotation_applied,
        "orientation_status": normalization.orientation_status,
        "external_margin_cropped": normalization.external_margin_cropped,
        "normalization_mode": normalization.normalization_mode,
        "skew_angle": normalization.skew_angle,
        "fields": fields,
        "metadata": metadata,
        "manifest": manifest,
    }


def collect_image_files(input_path: Path, limit: int | None = None) -> list[Path]:
    input_path = input_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"No existe la ruta de entrada: {input_path}")

    if input_path.is_file():
        if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Formato no soportado: {input_path}")
        return [input_path]

    image_files = sorted(
        path
        for path in input_path.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if limit is not None:
        image_files = image_files[:limit]

    return image_files


def process_directory(
    input_dir: Path = DEFAULT_INPUT_DIR,
    debug: bool = False,
    debug_dir: Path = DEFAULT_DEBUG_DIR,
    limit: int | None = None,
) -> list[dict]:
    image_files = collect_image_files(input_dir, limit)

    results: list[dict] = []

    for image_path in image_files:
        try:
            result = extract_field_crops(
                image_path=image_path,
                debug=debug,
                debug_dir=debug_dir,
            )

            results.append(result)

            problematic = sum(
                1
                for item in result["metadata"]
                if item.status != "OK"
            )

            print(
                f"{image_path.name}"
                f" | orientación={result['orientation_status']}"
                f" | rotación={result['rotation_applied']}"
                f" | skew={result['skew_angle']}°"
                f" | modo={result['normalization_mode']}"
                f" | margen_externo_recortado={result['external_margin_cropped']}"
                f" | campos_alerta={problematic}"
            )

        except Exception as error:
            print(f"ERROR {image_path.name}: {error}")

    return results


def write_batch_manifest(results: list[dict], output_path: Path) -> None:
    ensure_directory(output_path.parent)

    payload = {
        "total": len(results),
        "items": [
            result["manifest"]
            for result in results
        ],
    }

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extractor robusto de campos para actas electorales horizontales."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Carpeta o archivo PNG/JPG del acta.",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Guarda _original.png, _normalized.png, _regions.png, recortes y manifest.json.",
    )

    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=DEFAULT_DEBUG_DIR,
        help="Carpeta donde se guardan los artefactos debug.",
    )

    parser.add_argument(
        "--clean-debug",
        action="store_true",
        help="Elimina la carpeta debug antes de generar nuevos resultados.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Procesa solo las primeras N imágenes.",
    )

    parser.add_argument(
        "--batch-manifest",
        type=Path,
        default=None,
        help="Ruta opcional para guardar un JSON general de todas las actas procesadas.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.clean_debug and args.debug_dir.exists():
        shutil.rmtree(args.debug_dir)

    results = process_directory(
        input_dir=args.input,
        debug=args.debug,
        debug_dir=args.debug_dir,
        limit=args.limit,
    )

    print(f"\nActas procesadas: {len(results)}")

    if args.debug:
        print(f"Artefactos debug en: {args.debug_dir.resolve()}")

    if args.batch_manifest is not None:
        write_batch_manifest(results, args.batch_manifest)
        print(f"Manifest general guardado en: {args.batch_manifest.resolve()}")


if __name__ == "__main__":
    main()
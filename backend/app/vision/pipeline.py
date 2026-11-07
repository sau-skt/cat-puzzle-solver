"""Detect a colored cat-puzzle board in a screenshot.

The pipeline crops or perspective-corrects the board, finds the repeated cell
blobs between the light gaps, clusters cell colors in Lab space, and looks for
X marks and cat icons. Missing cells stay unknown. They are never filled in.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from app.vision.colors import bgr_to_hex, cluster_lab, name_bgr, sample_cell_color
from app.vision.marks import analyze_mark


class DetectionError(Exception):
    """Raised when the image does not contain a usable grid."""


@dataclass
class DetectedCell:
    row: int
    col: int
    color_id: int | None
    color_label: str | None
    color_hex: str | None
    blocked: bool
    has_cat: bool
    confidence: float
    bbox: tuple[int, int, int, int] | None


@dataclass
class DetectionResult:
    rows: int
    cols: int
    cells: list[DetectedCell]
    overall_confidence: float
    needs_review: bool
    notes: list[str] = field(default_factory=list)
    normalized_image: np.ndarray | None = None


@dataclass
class _Blob:
    x: int
    y: int
    w: int
    h: int
    area: float
    cx: float
    cy: float


def analyze_image(image_bgr: np.ndarray) -> DetectionResult:
    if image_bgr is None or image_bgr.size == 0:
        raise DetectionError("The image is empty.")
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise DetectionError("The image must be a color image.")
    height, width = image_bgr.shape[:2]
    if min(height, width) < 40:
        raise DetectionError("The image is too small to contain a puzzle grid.")
    if max(height, width) > 8000:
        raise DetectionError("The image is larger than the 8000 pixel limit.")

    direct = _grid_from_blobs(image_bgr)
    if direct is not None and direct[4] >= 0.9:
        return _build_result(direct[3][0], direct[0], direct[1], direct[2], True)

    board, _did_crop = _extract_board(image_bgr)
    if board is not image_bgr:
        recovered = _grid_from_blobs(board)
        if recovered is not None and (direct is None or recovered[4] > direct[4]):
            return _build_result(recovered[3][0], recovered[0], recovered[1], recovered[2], True)

    if direct is not None:
        return _build_result(direct[3][0], direct[0], direct[1], direct[2], True)
    raise DetectionError(
        "No puzzle grid was found. Upload a screenshot where the colored board is visible, or build the grid manually."
    )


def _grid_from_blobs(image: np.ndarray):
    """Return rows, cols, occupied blobs in crop coordinates, crop tuple, and coverage."""
    blobs = _find_cell_blobs(image)
    if len(blobs) < 4:
        return None
    rows, cols, occupied = _assign_grid(blobs)
    if rows < 2 or cols < 2:
        return None
    coverage = len(occupied) / float(rows * cols)
    pad = 6
    x1 = max(0, min(blob.x for blob in blobs) - pad)
    y1 = max(0, min(blob.y for blob in blobs) - pad)
    x2 = min(image.shape[1], max(blob.x + blob.w for blob in blobs) + pad)
    y2 = min(image.shape[0], max(blob.y + blob.h for blob in blobs) + pad)
    shifted: dict[tuple[int, int], _Blob] = {}
    for key, blob in occupied.items():
        shifted[key] = _Blob(
            blob.x - x1,
            blob.y - y1,
            blob.w,
            blob.h,
            blob.area,
            blob.cx - x1,
            blob.cy - y1,
        )
    crop = image[y1:y2, x1:x2].copy()
    return rows, cols, shifted, (crop, x1, y1), coverage


def _gap_mask(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    # Light, low-chroma gaps and page background. Dark marks stay inside cells.
    return (saturation < 42) & (value > 165)


def _extract_board(image: np.ndarray) -> tuple[np.ndarray, bool]:
    gap = _gap_mask(image)
    cell = np.where(gap, 0, 255).astype(np.uint8)
    cell = cv2.morphologyEx(cell, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    height, width = cell.shape
    kernel_size = max(3, int(round(min(height, width) * 0.018)))
    if kernel_size % 2 == 0:
        kernel_size += 1
    closed = cv2.morphologyEx(cell, cv2.MORPH_CLOSE, np.ones((kernel_size, kernel_size), np.uint8))
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = float(height * width)
    best = None
    best_score = 0.0
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < image_area * 0.08:
            continue
        _x, _y, box_w, box_h = cv2.boundingRect(contour)
        aspect = box_w / max(box_h, 1)
        if aspect < 0.65 or aspect > 1.55:
            continue
        squareness = 1.0 - min(abs(aspect - 1.0), 1.0)
        score = area * (0.45 + squareness)
        if score > best_score:
            best_score = score
            best = contour
    if best is None:
        return image, False
    _x, _y, box_w, box_h = cv2.boundingRect(best)
    rect = cv2.minAreaRect(best)
    angle = abs(float(rect[2]))
    near_axis = min(angle, abs(90 - angle), abs(180 - angle)) < 8
    if near_axis and box_w > 20 and box_h > 20:
        return image[_y : _y + box_h, _x : _x + box_w].copy(), True
    quad = _quad_from_contour(best)
    if _axis_aligned(quad):
        x1 = max(0, int(np.floor(np.min(quad[:, 0]))))
        y1 = max(0, int(np.floor(np.min(quad[:, 1]))))
        x2 = min(width, int(np.ceil(np.max(quad[:, 0]))))
        y2 = min(height, int(np.ceil(np.max(quad[:, 1]))))
        if x2 - x1 < 20 or y2 - y1 < 20:
            return image, False
        return image[y1:y2, x1:x2].copy(), True
    warped = _warp(image, quad)
    return warped, True


def _quad_from_contour(contour: np.ndarray) -> np.ndarray:
    perimeter = cv2.arcLength(contour, True)
    for epsilon in (0.008, 0.015, 0.025, 0.04, 0.06):
        approx = cv2.approxPolyDP(contour, epsilon * perimeter, True)
        if len(approx) == 4:
            return _order_corners(approx.reshape(4, 2).astype(np.float32))
    box = cv2.boxPoints(cv2.minAreaRect(contour))
    return _order_corners(box.astype(np.float32))


def _order_corners(points: np.ndarray) -> np.ndarray:
    summed = points.sum(axis=1)
    diff = np.diff(points, axis=1).reshape(-1)
    ordered = np.array(
        [
            points[int(np.argmin(summed))],
            points[int(np.argmin(diff))],
            points[int(np.argmax(summed))],
            points[int(np.argmax(diff))],
        ],
        dtype=np.float32,
    )
    return ordered


def _axis_aligned(quad: np.ndarray, tolerance_degrees: float = 4.0) -> bool:
    edges = [quad[(index + 1) % 4] - quad[index] for index in range(4)]
    for edge in edges:
        angle = abs(np.degrees(np.arctan2(edge[1], edge[0]))) % 180
        distance = min(angle, abs(90 - angle), abs(180 - angle))
        if distance > tolerance_degrees:
            return False
    return True


def _warp(image: np.ndarray, quad: np.ndarray) -> np.ndarray:
    top_left, top_right, bottom_right, bottom_left = quad
    width = int(round(max(np.linalg.norm(top_right - top_left), np.linalg.norm(bottom_right - bottom_left))))
    height = int(round(max(np.linalg.norm(bottom_left - top_left), np.linalg.norm(bottom_right - top_right))))
    width = max(width, 20)
    height = max(height, 20)
    destination = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(quad, destination)
    return cv2.warpPerspective(image, matrix, (width, height), flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))


def _find_cell_blobs(image: np.ndarray) -> list[_Blob]:
    mask = np.where(_gap_mask(image), 0, 255).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = float(image.shape[0] * image.shape[1])
    blobs: list[_Blob] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < image_area * 0.0015 or area > image_area * 0.22:
            continue
        x, y, width, height = cv2.boundingRect(contour)
        aspect = width / max(height, 1)
        if aspect < 0.72 or aspect > 1.4:
            continue
        if area / max(width * height, 1) < 0.5:
            continue
        blobs.append(_Blob(x, y, width, height, area, x + width / 2, y + height / 2))
    if len(blobs) < 4:
        return blobs
    areas = sorted(blob.area for blob in blobs)
    median_area = areas[len(areas) // 2]
    filtered = [blob for blob in blobs if median_area * 0.5 <= blob.area <= median_area * 1.85]
    return filtered if len(filtered) >= 4 else blobs


def _cluster_axis(values: list[float], minimum_gap: float) -> list[float]:
    ordered = sorted(values)
    groups: list[list[float]] = [[ordered[0]]]
    for value in ordered[1:]:
        if value - groups[-1][-1] > minimum_gap:
            groups.append([value])
        else:
            groups[-1].append(value)
    return [float(np.mean(group)) for group in groups]


def _nearest(value: float, centers: list[float]) -> int:
    return int(np.argmin([abs(value - center) for center in centers]))


def _assign_grid(blobs: list[_Blob]) -> tuple[int, int, dict[tuple[int, int], _Blob]]:
    median_height = float(np.median([blob.h for blob in blobs]))
    gap = max(4.0, median_height * 0.42)
    row_centers = _cluster_axis([blob.cy for blob in blobs], gap)
    col_centers = _cluster_axis([blob.cx for blob in blobs], gap)
    occupied: dict[tuple[int, int], _Blob] = {}
    for blob in blobs:
        key = (_nearest(blob.cy, row_centers), _nearest(blob.cx, col_centers))
        current = occupied.get(key)
        if current is None or blob.area > current.area:
            occupied[key] = blob
    return len(row_centers), len(col_centers), occupied


def _build_result(
    image: np.ndarray,
    rows: int,
    cols: int,
    occupied: dict[tuple[int, int], _Blob],
    cropped: bool,
) -> DetectionResult:
    notes: list[str] = []
    if not cropped:
        notes.append("The board was not cropped from a larger screenshot. Detection used the full image.")
    samples: list[np.ndarray] = []
    keys: list[tuple[int, int]] = []
    for row in range(rows):
        for col in range(cols):
            blob = occupied.get((row, col))
            if blob is None:
                continue
            roi = image[blob.y : blob.y + blob.h, blob.x : blob.x + blob.w]
            samples.append(sample_cell_color(roi))
            keys.append((row, col))
    labels = cluster_lab(samples)
    label_bgr: dict[int, np.ndarray] = {}
    buckets: dict[int, list[np.ndarray]] = {}
    for label, sample in zip(labels, samples, strict=True):
        buckets.setdefault(label, []).append(sample)
    for label, members in buckets.items():
        label_bgr[label] = np.median(np.vstack(members), axis=0)

    cells: list[DetectedCell] = []
    confidences: list[float] = []
    missing = 0
    for row in range(rows):
        for col in range(cols):
            blob = occupied.get((row, col))
            if blob is None:
                missing += 1
                cells.append(
                    DetectedCell(row, col, None, None, None, False, False, 0.0, None)
                )
                confidences.append(0.0)
                continue
            sample_index = keys.index((row, col))
            label = labels[sample_index]
            mean = label_bgr[label]
            roi = image[blob.y : blob.y + blob.h, blob.x : blob.x + blob.w]
            blocked, has_cat, mark_confidence = analyze_mark(roi)
            color_distance = _lab_distance(samples[sample_index], mean)
            color_confidence = float(np.clip(1.0 - color_distance / 40.0, 0.35, 0.98))
            confidence = float(np.clip(0.5 * color_confidence + 0.5 * mark_confidence, 0.0, 0.99))
            if blocked and has_cat:
                has_cat = False
                confidence *= 0.7
                notes.append(f"Row {row + 1}, column {col + 1} looked both blocked and occupied. It was kept as blocked.")
            cells.append(
                DetectedCell(
                    row=row,
                    col=col,
                    color_id=int(label),
                    color_label=name_bgr(mean),
                    color_hex=bgr_to_hex(mean),
                    blocked=blocked,
                    has_cat=has_cat,
                    confidence=confidence,
                    bbox=(int(blob.x), int(blob.y), int(blob.w), int(blob.h)),
                )
            )
            confidences.append(confidence)

    coverage = 1.0 - (missing / max(rows * cols, 1))
    overall = float(np.clip(float(np.mean(confidences)) * (0.55 + 0.45 * coverage), 0.0, 0.99))
    if rows != cols:
        notes.append(f"Detected a {rows}×{cols} board. The standard rules need a square grid.")
        overall *= 0.75
    if missing:
        notes.append(f"{missing} cell{'s' if missing != 1 else ''} could not be read and {'were' if missing != 1 else 'was'} left blank.")
    ambiguous = [cell for cell in cells if cell.color_id is not None and cell.confidence < 0.55]
    if ambiguous:
        notes.append(f"{len(ambiguous)} cells have low detection confidence. Please review them.")
    needs_review = overall < 0.8 or missing > 0 or rows != cols or any(cell.confidence < 0.5 for cell in cells)
    if needs_review and not notes:
        notes.append("Detection confidence is low. Review the board before solving.")
    return DetectionResult(
        rows=rows,
        cols=cols,
        cells=cells,
        overall_confidence=overall,
        needs_review=needs_review,
        notes=notes,
        normalized_image=image,
    )


def _lab_distance(bgr_a: np.ndarray, bgr_b: np.ndarray) -> float:
    pair = np.uint8(np.round(np.vstack([bgr_a, bgr_b]))).reshape(2, 1, 3)
    labs = cv2.cvtColor(pair, cv2.COLOR_BGR2LAB).reshape(2, 3).astype(np.float32)
    return float(np.linalg.norm(labs[0] - labs[1]))

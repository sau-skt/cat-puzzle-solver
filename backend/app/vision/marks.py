"""Detect blocked X marks and existing cat icons inside a cell."""

from __future__ import annotations

import cv2
import numpy as np


def _x_template(height: int, width: int) -> np.ndarray:
    mask = np.zeros((height, width), np.uint8)
    thickness = max(1, int(round(min(height, width) * 0.12)))
    cv2.line(mask, (0, 0), (width - 1, height - 1), 255, thickness)
    cv2.line(mask, (width - 1, 0), (0, height - 1), 255, thickness)
    return mask > 0


def analyze_mark(roi: np.ndarray) -> tuple[bool, bool, float]:
    """Return (blocked, has_cat, mark_confidence).

    An X is a thin dark diagonal pair. A cat is a compact central blob that is
    not explained by those diagonals. Ambiguous marks lower the confidence.
    """
    if roi.size == 0:
        return False, False, 0.2
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    margin_y = max(1, int(height * 0.16))
    margin_x = max(1, int(width * 0.16))
    inner = gray[margin_y : height - margin_y, margin_x : width - margin_x]
    if inner.size == 0:
        return False, False, 0.3
    background = float(np.median(inner))
    dark = inner < max(30, background - 45)
    dark_ratio = float(dark.mean())
    template = _x_template(*inner.shape)
    template_mass = float(template.sum()) or 1.0
    on_diagonal = float(dark[template].mean()) if template.any() else 0.0
    off_diagonal = float(dark[~template].mean()) if (~template).any() else 0.0
    x_coverage = float((dark & template).sum()) / template_mass

    # A real X puts dark pixels on both diagonals and leaves the rest of the cell alone.
    # Cat icons also cross the diagonals, but they fill the off-diagonal area too.
    blocked = on_diagonal > 0.62 and off_diagonal < 0.2 and 0.04 < dark_ratio < 0.58 and x_coverage > 0.5
    has_cat = False
    if not blocked and 0.05 < dark_ratio < 0.62:
        dark_u8 = dark.astype(np.uint8) * 255
        contours, _ = cv2.findContours(dark_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            circularity = 0.0 if perimeter <= 0 else float(4 * np.pi * area / (perimeter * perimeter))
            fill = area / max(inner.size, 1)
            if fill > 0.06 and circularity > 0.35 and off_diagonal > 0.08:
                has_cat = True

    if blocked:
        confidence = float(np.clip(0.55 + on_diagonal - off_diagonal, 0.45, 0.98))
    elif has_cat:
        confidence = 0.72
    else:
        confidence = 0.9 if dark_ratio < 0.04 else 0.62
    return blocked, has_cat, confidence

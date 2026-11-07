"""Draw a solved board, either on the normalized screenshot or as a fresh grid."""

from __future__ import annotations

import cv2
import numpy as np

from app.vision.synthetic import _draw_cat, _rounded_rect


def render_solution_image(
    *,
    rows: int,
    cols: int,
    color_hex: list[list[str | None]],
    placements: list[tuple[int, int]],
    background: np.ndarray | None = None,
    boxes: list[list[tuple[int, int, int, int] | None]] | None = None,
) -> np.ndarray:
    if background is not None and boxes is not None and _boxes_fit(background, boxes, rows, cols):
        canvas = background.copy()
        for row, col in placements:
            box = boxes[row][col]
            if box is None:
                continue
            x, y, width, height = box
            _highlight(canvas, x, y, width, height)
            _draw_cat(canvas, x, y, min(width, height))
            _label(canvas, x, y, f"R{row + 1} C{col + 1}")
        return _add_margin_with_indices(canvas, rows, cols, boxes)
    return _schematic(rows, cols, color_hex, placements)


def _boxes_fit(
    image: np.ndarray,
    boxes: list[list[tuple[int, int, int, int] | None]],
    rows: int,
    cols: int,
) -> bool:
    height, width = image.shape[:2]
    if len(boxes) != rows:
        return False
    for row in boxes:
        if len(row) != cols:
            return False
        for box in row:
            if box is None:
                continue
            x, y, box_w, box_h = box
            if x < 0 or y < 0 or x + box_w > width or y + box_h > height:
                return False
    return True


def _highlight(image: np.ndarray, x: int, y: int, width: int, height: int) -> None:
    overlay = image.copy()
    cv2.rectangle(overlay, (x, y), (x + width, y + height), (255, 255, 255), 3)
    cv2.addWeighted(overlay, 0.85, image, 0.15, 0, image)
    cv2.rectangle(image, (x + 1, y + 1), (x + width - 1, y + height - 1), (30, 30, 30), 2)


def _label(image: np.ndarray, x: int, y: int, text: str) -> None:
    cv2.putText(image, text, (x + 4, max(14, y + 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(image, text, (x + 4, max(14, y + 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (20, 20, 20), 1, cv2.LINE_AA)


def _add_margin_with_indices(
    image: np.ndarray,
    rows: int,
    cols: int,
    boxes: list[list[tuple[int, int, int, int] | None]],
) -> np.ndarray:
    margin = 28
    height, width = image.shape[:2]
    canvas = np.full((height + margin, width + margin, 3), (250, 247, 242), np.uint8)
    canvas[margin:, margin:] = image
    for row in range(rows):
        box = next((item for item in boxes[row] if item is not None), None)
        if box is None:
            continue
        _y = margin + box[1] + box[3] // 2
        cv2.putText(canvas, str(row + 1), (6, _y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (40, 30, 20), 1, cv2.LINE_AA)
    for col in range(cols):
        box = next((boxes[row][col] for row in range(rows) if boxes[row][col] is not None), None)
        if box is None:
            continue
        _x = margin + box[0] + box[2] // 2
        cv2.putText(canvas, str(col + 1), (_x, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (40, 30, 20), 1, cv2.LINE_AA)
    return canvas


def _schematic(
    rows: int,
    cols: int,
    color_hex: list[list[str | None]],
    placements: list[tuple[int, int]],
) -> np.ndarray:
    cell = 48
    gap = 6
    margin = 32
    width = margin * 2 + cols * cell + (cols - 1) * gap
    height = margin * 2 + rows * cell + (rows - 1) * gap
    canvas = np.full((height, width, 3), (246, 241, 232), np.uint8)
    placed = set(placements)
    for row in range(rows):
        cv2.putText(canvas, str(row + 1), (8, margin + row * (cell + gap) + cell // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (40, 30, 20), 1)
        for col in range(cols):
            if row == 0:
                x_label = margin + col * (cell + gap) + cell // 2
                cv2.putText(canvas, str(col + 1), (x_label, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (40, 30, 20), 1)
            x = margin + col * (cell + gap)
            y = margin + row * (cell + gap)
            _rounded_rect(canvas, x, y, cell, cell, 8, _hex_to_bgr(color_hex[row][col]))
            if (row, col) in placed:
                _highlight(canvas, x, y, cell, cell)
                _draw_cat(canvas, x, y, cell)
    return canvas


def _hex_to_bgr(value: str | None) -> tuple[int, int, int]:
    if not value or len(value) != 7:
        return (180, 180, 180)
    red = int(value[1:3], 16)
    green = int(value[3:5], 16)
    blue = int(value[5:7], 16)
    return (blue, green, red)

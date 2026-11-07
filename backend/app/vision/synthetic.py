"""Draw puzzle screenshots with a known ground truth for tests and fixtures."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Distinct BGR colors. They stay far apart in Lab after light JPEG compression.
PALETTE: list[tuple[str, tuple[int, int, int]]] = [
    ("red", (40, 40, 210)),
    ("orange", (30, 120, 230)),
    ("yellow", (40, 210, 230)),
    ("green", (50, 150, 40)),
    ("cyan", (200, 180, 30)),
    ("blue", (190, 70, 30)),
    ("purple", (150, 40, 140)),
    ("pink", (180, 110, 230)),
    ("brown", (40, 70, 120)),
    ("lime", (70, 210, 110)),
]


@dataclass
class SyntheticPuzzle:
    image: np.ndarray
    rows: int
    cols: int
    color_ids: list[list[int]]
    blocked: list[tuple[int, int]]
    cats: list[tuple[int, int]]
    color_names: list[str]


def render_puzzle(
    color_ids: list[list[int]],
    blocked: list[tuple[int, int]] | None = None,
    cats: list[tuple[int, int]] | None = None,
    *,
    cell: int = 52,
    gap: int = 8,
    margin: int = 36,
    background: tuple[int, int, int] = (244, 244, 246),
    header: int = 0,
) -> SyntheticPuzzle:
    rows = len(color_ids)
    cols = len(color_ids[0])
    blocked_set = set(blocked or [])
    cat_set = set(cats or [])
    width = margin * 2 + cols * cell + (cols - 1) * gap
    height = margin * 2 + rows * cell + (rows - 1) * gap + header
    canvas = np.full((height, width, 3), background, np.uint8)
    if header:
        canvas[0:header, :] = (32, 28, 26)
        cv2.rectangle(canvas, (18, header // 3), (70, header // 3 + 16), (90, 80, 70), -1)
    top = header + margin
    for row in range(rows):
        for col in range(cols):
            x = margin + col * (cell + gap)
            y = top + row * (cell + gap)
            color = PALETTE[color_ids[row][col] % len(PALETTE)][1]
            _rounded_rect(canvas, x, y, cell, cell, 10, color)
            if (row, col) in blocked_set:
                _draw_x(canvas, x, y, cell)
            if (row, col) in cat_set:
                _draw_cat(canvas, x, y, cell)
    return SyntheticPuzzle(
        image=canvas,
        rows=rows,
        cols=cols,
        color_ids=color_ids,
        blocked=sorted(blocked_set),
        cats=sorted(cat_set),
        color_names=[name for name, _bgr in PALETTE],
    )


def latin_color_ids(size: int, salt: int = 0) -> list[list[int]]:
    return [[(row * 3 + col * 7 + salt) % size for col in range(size)] for row in range(size)]


def perspective_warp(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    source = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    destination = np.float32(
        [
            [width * 0.08, height * 0.06],
            [width * 0.93, height * 0.02],
            [width * 0.98, height * 0.94],
            [width * 0.04, height * 0.9],
        ]
    )
    matrix = cv2.getPerspectiveTransform(source, destination)
    return cv2.warpPerspective(image, matrix, (width, height), borderValue=(244, 244, 246))


def _rounded_rect(image: np.ndarray, x: int, y: int, width: int, height: int, radius: int, color: tuple[int, int, int]) -> None:
    radius = min(radius, width // 2, height // 2)
    cv2.rectangle(image, (x + radius, y), (x + width - radius, y + height), color, -1)
    cv2.rectangle(image, (x, y + radius), (x + width, y + height - radius), color, -1)
    cv2.circle(image, (x + radius, y + radius), radius, color, -1)
    cv2.circle(image, (x + width - radius, y + radius), radius, color, -1)
    cv2.circle(image, (x + radius, y + height - radius), radius, color, -1)
    cv2.circle(image, (x + width - radius, y + height - radius), radius, color, -1)


def _draw_x(image: np.ndarray, x: int, y: int, cell: int) -> None:
    pad = int(cell * 0.22)
    thickness = max(2, cell // 10)
    color = (25, 25, 25)
    cv2.line(image, (x + pad, y + pad), (x + cell - pad, y + cell - pad), color, thickness, cv2.LINE_AA)
    cv2.line(image, (x + cell - pad, y + pad), (x + pad, y + cell - pad), color, thickness, cv2.LINE_AA)


def _draw_cat(image: np.ndarray, x: int, y: int, cell: int) -> None:
    center = (x + cell // 2, y + int(cell * 0.58))
    radius = int(cell * 0.22)
    color = (20, 20, 20)
    cv2.circle(image, center, radius, color, -1, cv2.LINE_AA)
    ear_h = int(cell * 0.16)
    left = np.array(
        [
            [center[0] - radius, center[1] - radius // 3],
            [center[0] - radius // 2, center[1] - radius - ear_h],
            [center[0] - radius // 5, center[1] - radius // 4],
        ]
    )
    right = np.array(
        [
            [center[0] + radius, center[1] - radius // 3],
            [center[0] + radius // 2, center[1] - radius - ear_h],
            [center[0] + radius // 5, center[1] - radius // 4],
        ]
    )
    cv2.fillConvexPoly(image, left, color, cv2.LINE_AA)
    cv2.fillConvexPoly(image, right, color, cv2.LINE_AA)
    eye = max(2, cell // 18)
    cv2.circle(image, (center[0] - radius // 3, center[1] - 2), eye, (240, 240, 240), -1)
    cv2.circle(image, (center[0] + radius // 3, center[1] - 2), eye, (240, 240, 240), -1)

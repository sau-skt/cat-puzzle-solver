"""Color naming and clustering in CIE Lab."""

from __future__ import annotations

import cv2
import numpy as np

# Hue ranges are in OpenCV degrees (0-180).
_NAMED_HUES: list[tuple[str, int, int]] = [
    ("red", 0, 8),
    ("orange", 8, 20),
    ("yellow", 20, 35),
    ("lime", 35, 50),
    ("green", 50, 75),
    ("cyan", 75, 95),
    ("blue", 95, 125),
    ("purple", 125, 150),
    ("pink", 150, 175),
    ("red", 175, 181),
]


def bgr_to_hex(bgr: np.ndarray) -> str:
    blue, green, red = [int(np.clip(round(float(channel)), 0, 255)) for channel in bgr[:3]]
    return f"#{red:02x}{green:02x}{blue:02x}"


def name_bgr(bgr: np.ndarray) -> str:
    pixel = np.uint8([[np.clip(np.round(bgr), 0, 255).astype(np.uint8)]])
    hue, saturation, value = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0, 0]
    hue_i = int(hue)
    sat_i = int(saturation)
    val_i = int(value)
    if val_i < 45:
        return "black"
    if sat_i < 30 and val_i > 210:
        return "white"
    if sat_i < 35:
        return "gray"
    if 8 <= hue_i <= 25 and sat_i < 180 and val_i < 170:
        return "brown"
    for name, start, end in _NAMED_HUES:
        if start <= hue_i < end:
            return name
    return "unknown"


def sample_cell_color(roi: np.ndarray) -> np.ndarray:
    """Median of chromatic pixels, so rounded corners, gaps, and dark marks do not tint the cell."""
    if roi.size == 0:
        return np.array([0, 0, 0], dtype=np.float32)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    chromatic = hsv[:, :, 1] > 40
    pixels = roi.reshape(-1, 3)
    chosen = pixels[chromatic.reshape(-1)]
    if chosen.shape[0] < 8:
        return np.median(pixels, axis=0)
    return np.median(chosen, axis=0)


def cluster_lab(colors_bgr: list[np.ndarray], threshold: float = 26.0) -> list[int]:
    """Greedy Lab clustering. Returns a label per input color, stable by first-seen order."""
    if not colors_bgr:
        return []
    pixels = np.uint8(np.round(np.vstack(colors_bgr))).reshape(-1, 1, 3)
    labs = cv2.cvtColor(pixels, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    means: list[np.ndarray] = []
    members: list[list[int]] = []
    labels = [-1] * len(labs)
    for index, lab in enumerate(labs):
        best = -1
        best_distance = 1e9
        for cluster_index, mean in enumerate(means):
            distance = float(np.linalg.norm(lab - mean))
            if distance < best_distance:
                best_distance = distance
                best = cluster_index
        if best >= 0 and best_distance <= threshold:
            members[best].append(index)
            means[best] = np.mean(labs[members[best]], axis=0)
            labels[index] = best
        else:
            labels[index] = len(means)
            means.append(lab.copy())
            members.append([index])
    return labels

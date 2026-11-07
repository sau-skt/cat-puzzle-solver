"""Write the sample screenshot dataset under tests/fixtures."""

import json
from pathlib import Path

import cv2
import numpy as np

from app.vision.synthetic import latin_color_ids, perspective_warp, render_puzzle

ROOT = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def write_png(name: str, image: np.ndarray, meta: dict) -> None:
    path = ROOT / name
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(f"Could not encode {name}")
    path.write_bytes(encoded.tobytes())
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2))


def meta(puzzle, extra: dict | None = None) -> dict:
    payload = {
        "rows": puzzle.rows,
        "cols": puzzle.cols,
        "color_ids": puzzle.color_ids,
        "blocked": puzzle.blocked,
        "cats": puzzle.cats,
    }
    if extra:
        payload.update(extra)
    return payload


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    ten = render_puzzle(
        latin_color_ids(10),
        blocked=[(0, 1), (2, 4), (5, 8), (9, 0)],
        cats=[(4, 6)],
        cell=46,
        gap=7,
        margin=28,
    )
    write_png("valid_10x10.png", ten.image, meta(ten, {"notes": "10x10 board with blocked cells and one existing cat."}))

    eight = render_puzzle(latin_color_ids(8, salt=1), blocked=[(1, 1), (3, 6), (7, 2)], cell=32, gap=5, margin=18)
    write_png("board_8x8_small.png", eight.image, meta(eight, {"notes": "Smaller 8x8 resolution."}))

    large = render_puzzle(latin_color_ids(8, salt=1), blocked=[(1, 1), (3, 6), (7, 2)], cell=68, gap=8, margin=24)
    write_png("board_8x8_large.png", large.image, meta(large))

    headed = render_puzzle(latin_color_ids(6), blocked=[(0, 2), (4, 5)], cell=44, gap=8, margin=30, header=86)
    ok, jpeg = cv2.imencode(".jpg", headed.image, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
    if not ok:
        raise RuntimeError("jpeg encode failed")
    (ROOT / "header_screenshot.jpg").write_bytes(jpeg.tobytes())
    (ROOT / "header_screenshot.json").write_text(json.dumps(meta(headed, {"compression": "jpeg-q72", "header": True}), indent=2))

    skewed = render_puzzle(latin_color_ids(5), blocked=[(1, 3)], cats=[(3, 1)], cell=58, gap=10, margin=34)
    write_png("perspective.png", perspective_warp(skewed.image), meta(skewed, {"perspective": True}))

    noise = np.random.default_rng(3).integers(0, 255, size=(220, 260, 3), dtype=np.uint8)
    write_png("noise.png", noise, {"expect": "low_confidence_or_detection_error"})

    (ROOT / "logical_cases.json").write_text(
        json.dumps(
            {
                "multiple_solutions": {
                    "colors": [[col for col in range(4)] for _ in range(4)],
                    "blocked": [],
                    "expect": "multiple",
                },
                "no_solution": {
                    "colors": [[col for col in range(4)] for _ in range(4)],
                    "blocked": [[0, col] for col in range(4)],
                    "expect": "none",
                },
            },
            indent=2,
        )
    )
    print(f"Wrote fixtures to {ROOT}")


if __name__ == "__main__":
    main()

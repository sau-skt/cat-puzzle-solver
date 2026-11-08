"""Grid, color, and mark detection against drawn screenshots."""

import cv2
import numpy as np
import pytest

from app.vision.colors import cluster_lab
from app.vision.pipeline import DetectionError, analyze_image
from app.vision.synthetic import latin_color_ids, perspective_warp, render_puzzle


def _partition(pairs):
    groups: dict[int, set[tuple[int, int]]] = {}
    for key, row, col in pairs:
        groups.setdefault(key, set()).add((row, col))
    return {frozenset(value) for value in groups.values()}


def _assert_matches(image, puzzle):
    result = analyze_image(image)
    assert (result.rows, result.cols) == (puzzle.rows, puzzle.cols)
    assert result.overall_confidence >= 0.8
    assert result.needs_review is False
    detected_colors = _partition(
        (cell.color_id, cell.row, cell.col) for cell in result.cells if cell.color_id is not None
    )
    expected_colors = _partition(
        (puzzle.color_ids[row][col], row, col) for row in range(puzzle.rows) for col in range(puzzle.cols)
    )
    assert detected_colors == expected_colors
    assert {(cell.row, cell.col) for cell in result.cells if cell.blocked} == set(puzzle.blocked)
    assert {(cell.row, cell.col) for cell in result.cells if cell.has_cat} == set(puzzle.cats)
    assert all(cell.confidence >= 0.5 for cell in result.cells)
    return result


def test_ten_by_ten_with_blocked_cells_and_a_cat():
    colors = latin_color_ids(10)
    blocked = [(0, 1), (2, 4), (5, 8), (9, 0)]
    cats = [(4, 6)]
    puzzle = render_puzzle(colors, blocked=blocked, cats=cats, cell=46, gap=7, margin=28)
    _assert_matches(puzzle.image, puzzle)


def test_blocked_board_at_two_resolutions():
    colors = latin_color_ids(8, salt=1)
    blocked = [(1, 1), (3, 6), (7, 2)]
    for cell in (32, 68):
        puzzle = render_puzzle(colors, blocked=blocked, cell=cell, gap=max(5, cell // 8), margin=20)
        _assert_matches(puzzle.image, puzzle)


def test_screenshot_layout_with_header_and_jpeg_compression():
    colors = latin_color_ids(6)
    blocked = [(0, 2), (4, 5)]
    puzzle = render_puzzle(colors, blocked=blocked, cell=44, gap=8, margin=30, header=86)
    ok, encoded = cv2.imencode(".jpg", puzzle.image, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
    assert ok
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    _assert_matches(decoded, puzzle)


def test_perspective_screenshot():
    colors = latin_color_ids(5)
    blocked = [(1, 3)]
    cats = [(3, 1)]
    puzzle = render_puzzle(colors, blocked=blocked, cats=cats, cell=58, gap=10, margin=34)
    warped = perspective_warp(puzzle.image)
    _assert_matches(warped, puzzle)


def test_noise_is_not_reported_as_a_confident_grid():
    noise = np.random.default_rng(3).integers(0, 255, size=(220, 260, 3), dtype=np.uint8)
    try:
        result = analyze_image(noise)
    except DetectionError:
        return
    assert result.needs_review or result.overall_confidence < 0.55
    assert not (result.rows >= 8 and result.cols >= 8 and result.overall_confidence > 0.85 and not result.needs_review)


def test_dusty_blue_and_sky_blue_stay_separate():
    dusty = np.array([215, 191, 167], dtype=np.float32)
    sky = np.array([231, 188, 107], dtype=np.float32)
    labels = cluster_lab([dusty, sky, dusty, sky])
    assert labels == [0, 1, 0, 1]


def test_tiny_image_is_rejected():
    tiny = np.zeros((20, 20, 3), dtype=np.uint8)
    with pytest.raises(DetectionError):
        analyze_image(tiny)

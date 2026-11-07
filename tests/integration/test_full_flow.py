"""Signup through history for a generated puzzle screenshot."""

import cv2
import numpy as np

from app.solver.validate import CellView, validate_solution
from app.vision.synthetic import render_puzzle


def _signup(client, email, password, phone):
    response = client.post(
        "/api/auth/signup",
        json={
            "full_name": "Saurabh Singh",
            "email": email,
            "country_iso": "IN",
            "dial_code": "+91",
            "phone_number": phone,
            "password": password,
            "confirm_password": password,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_analyze_correct_solve_history_and_isolation(client, strong_password):
    owner = _signup(client, "owner@example.com", strong_password, "9000000001")
    colors = [[col for col in range(6)] for _ in range(6)]
    blocked = [(0, 1), (2, 2), (5, 0)]
    puzzle_image = render_puzzle(colors, blocked=blocked, cell=50, gap=8, margin=24, header=70)
    ok, encoded = cv2.imencode(".png", puzzle_image.image)
    assert ok

    rejected = client.post("/api/puzzles/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert rejected.status_code == 400

    uploaded = client.post(
        "/api/puzzles/upload",
        files={"file": ("board.png", encoded.tobytes(), "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    puzzle_id = uploaded.json()["id"]

    analyzed = client.post(f"/api/puzzles/{puzzle_id}/analyze")
    assert analyzed.status_code == 200, analyzed.text
    screenshot = client.get(f"/api/puzzles/{puzzle_id}/image")
    assert screenshot.status_code == 200
    assert screenshot.headers["content-type"].startswith("image/")
    board = analyzed.json()
    assert board["rows"] == 6 and board["cols"] == 6
    assert board["needs_review"] is False
    detected_blocked = {(cell["row"], cell["col"]) for cell in board["cells"] if cell["blocked"]}
    assert detected_blocked == set(blocked)

    edited = board["cells"]
    edited.sort(key=lambda cell: (cell["row"], cell["col"]))
    # Correct a cell explicitly, then change it back, to exercise the editor API.
    target = next(cell for cell in edited if cell["row"] == 1 and cell["col"] == 1)
    original_label = target["color_label"]
    target["color_label"] = "corrected"
    target["has_cat"] = False
    saved = client.put(
        f"/api/puzzles/{puzzle_id}/board",
        json={"rows": 6, "cols": 6, "rules": board["rules"], "cells": edited},
    )
    assert saved.status_code == 200, saved.text
    target["color_label"] = original_label
    saved = client.put(
        f"/api/puzzles/{puzzle_id}/board",
        json={"rows": 6, "cols": 6, "rules": board["rules"], "cells": edited},
    )
    assert saved.status_code == 200

    solved = client.post(f"/api/puzzles/{puzzle_id}/solve")
    assert solved.status_code == 200, solved.text
    outcome = solved.json()
    assert outcome["status"] in {"unique", "multiple"}
    assert outcome["solutions_found"] >= 1
    assert outcome["solutions"][0]["validation_passed"] is True
    placements = [(item["row"], item["col"]) for item in outcome["solutions"][0]["placements"]]
    grid = [
        [
            CellView(
                row=row,
                col=col,
                color_id=next(cell["color_id"] for cell in edited if cell["row"] == row and cell["col"] == col),
                blocked=next(cell["blocked"] for cell in edited if cell["row"] == row and cell["col"] == col),
            )
            for col in range(6)
        ]
        for row in range(6)
    ]
    assert validate_solution(grid, placements) == []
    assert all(spot not in blocked for spot in placements)

    image = client.get(f"/api/puzzles/{puzzle_id}/solutions/{outcome['solutions'][0]['id']}/image")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    decoded = cv2.imdecode(np.frombuffer(image.content, np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None and decoded.size > 0

    history = client.get("/api/puzzles")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    detail = client.get(f"/api/puzzles/{puzzle_id}")
    assert detail.status_code == 200
    assert detail.json()["solution_count"] >= 1
    stats = client.get("/api/puzzles/stats")
    assert stats.json()["solved"] == 1

    client.post("/api/auth/logout")
    _signup(client, "other@example.com", strong_password, "9000000002")
    hidden = client.get(f"/api/puzzles/{puzzle_id}")
    assert hidden.status_code == 404
    hidden_image = client.get(f"/api/puzzles/{puzzle_id}/solutions/{outcome['solutions'][0]['id']}/image")
    assert hidden_image.status_code == 404

    client.post("/api/auth/logout")
    client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": strong_password, "remember_me": False},
    )
    reopened = client.get(f"/api/puzzles/{puzzle_id}/solutions")
    assert reopened.status_code == 200
    assert len(reopened.json()) >= 1
    assert client.delete(f"/api/puzzles/{puzzle_id}").status_code == 204
    assert client.get(f"/api/puzzles/{puzzle_id}").status_code == 404
    assert client.get("/api/puzzles").json()["total"] == 0
    assert owner["email"] == "owner@example.com"

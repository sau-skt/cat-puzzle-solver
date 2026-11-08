"""Upload, recognition, editing, solving, and history."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.puzzle import Puzzle, PuzzleCell, PuzzleSolution, SolutionPosition
from app.models.types import utcnow
from app.models.user import User
from app.schemas.puzzle import (
    BoardResponse,
    BoardUpdate,
    CellResponse,
    PlacementResponse,
    PuzzleDetail,
    PuzzleListResponse,
    PuzzleSummary,
    RulesModel,
    SolutionResponse,
    SolveResponse,
    StatsResponse,
)
from app.services.storage import delete_tree, read_bytes, save_bytes
from app.solver.engine import solve_board
from app.solver.validate import CellView, RuleSet, validate_solution
from app.vision.pipeline import DetectionError, analyze_image
from app.vision.render import render_solution_image

logger = logging.getLogger("catpuzzle.puzzles")

_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"


def list_puzzles(db: Session, user: User, limit: int, offset: int) -> PuzzleListResponse:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    total = db.scalar(select(func.count()).select_from(Puzzle).where(Puzzle.user_id == user.id)) or 0
    rows = db.scalars(
        select(Puzzle)
        .where(Puzzle.user_id == user.id)
        .order_by(Puzzle.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return PuzzleListResponse(items=[_summary(row) for row in rows], total=total)


def stats_for(db: Session, user: User) -> StatsResponse:
    rows = db.scalars(select(Puzzle).where(Puzzle.user_id == user.id).order_by(Puzzle.created_at.desc())).all()
    solved = sum(1 for row in rows if row.solver_status in {"unique", "multiple"})
    none = sum(1 for row in rows if row.solver_status == "none")
    total = len(rows)
    finished = solved + none
    return StatsResponse(
        total=total,
        solved=solved,
        no_solution=none,
        in_progress=total - finished,
        success_rate=round(solved / finished, 4) if finished else 0.0,
        recent=[_summary(row) for row in rows[:5]],
    )


def get_puzzle(db: Session, user: User, puzzle_id: str) -> PuzzleDetail:
    puzzle = _owned(db, user, puzzle_id)
    return _detail(puzzle)


def delete_puzzle(db: Session, user: User, puzzle_id: str) -> None:
    puzzle = _owned(db, user, puzzle_id)
    delete_tree(f"{user.id}/{puzzle.id}")
    db.delete(puzzle)
    db.commit()
    logger.info("Deleted puzzle %s for user %s", puzzle_id, user.id)


async def create_upload(db: Session, user: User, file: UploadFile) -> PuzzleDetail:
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Images must be 8 MB or smaller.")
    kind = _image_kind(data)
    if kind is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a PNG, JPG, JPEG, or WEBP screenshot.",
        )
    if not _pillow_accepts(data):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is not a valid image.")
    previous_ids = [puzzle.id for puzzle in db.scalars(select(Puzzle).where(Puzzle.user_id == user.id)).all()]
    for old_id in previous_ids:
        db.delete(_owned(db, user, old_id, load_cells=True, load_solutions=True))
    puzzle_id = str(uuid4())
    relative = f"{user.id}/{puzzle_id}/original.{kind if kind != 'jpeg' else 'jpg'}"
    save_bytes(relative, data)
    puzzle = Puzzle(
        id=puzzle_id,
        user_id=user.id,
        original_filename=(file.filename or "puzzle")[:255],
        original_image_path=relative,
        rules_json=json.dumps(RulesModel().model_dump()),
        status="uploaded",
    )
    db.add(puzzle)
    db.commit()
    for old_id in previous_ids:
        delete_tree(f"{user.id}/{old_id}")
    db.refresh(puzzle)
    logger.info("Stored upload %s for user %s, replacing %s", puzzle.id, user.id, len(previous_ids))
    return _detail(puzzle)


def analyze_puzzle(db: Session, user: User, puzzle_id: str) -> BoardResponse:
    puzzle = _owned(db, user, puzzle_id)
    image = _load_bgr(puzzle.original_image_path)
    try:
        detected = analyze_image(image)
    except DetectionError as exc:
        puzzle.status = "failed"
        puzzle.needs_review = True
        puzzle.detection_confidence = 0.0
        puzzle.detection_notes = str(exc)
        puzzle.rows = None
        puzzle.cols = None
        puzzle.cells.clear()
        puzzle.updated_at = utcnow()
        db.commit()
        logger.info("Detection failed for %s: %s", puzzle.id, exc)
        return _board(puzzle)
    _replace_cells_from_detection(puzzle, detected)
    relative = f"{user.id}/{puzzle.id}/normalized.png"
    _write_png(relative, detected.normalized_image)
    puzzle.normalized_image_path = relative
    puzzle.rows = detected.rows
    puzzle.cols = detected.cols
    puzzle.detection_confidence = detected.overall_confidence
    puzzle.needs_review = detected.needs_review
    puzzle.detection_notes = "\n".join(detected.notes) if detected.notes else None
    puzzle.status = "needs_review" if detected.needs_review else "analyzed"
    puzzle.solver_status = None
    puzzle.solution_count = 0
    puzzle.solutions.clear()
    puzzle.updated_at = utcnow()
    db.commit()
    db.refresh(puzzle)
    logger.info(
        "Analyzed %s as %sx%s confidence %.2f",
        puzzle.id,
        puzzle.rows,
        puzzle.cols,
        puzzle.detection_confidence or 0,
    )
    return _board(puzzle)


def get_board(db: Session, user: User, puzzle_id: str) -> BoardResponse:
    return _board(_owned(db, user, puzzle_id))


def update_board(db: Session, user: User, puzzle_id: str, payload: BoardUpdate) -> BoardResponse:
    puzzle = _owned(db, user, puzzle_id, load_cells=True)
    _validate_board_payload(payload)
    previous = {(cell.row, cell.col): cell for cell in puzzle.cells}
    keep_geometry = puzzle.rows == payload.rows and puzzle.cols == payload.cols
    puzzle.cells.clear()
    db.flush()
    for item in payload.cells:
        prior = previous.get((item.row, item.col)) if keep_geometry else None
        puzzle.cells.append(
            PuzzleCell(
                puzzle_id=puzzle.id,
                row=item.row,
                col=item.col,
                color_id=item.color_id,
                color_label=item.color_label,
                color_hex=item.color_hex,
                blocked=item.blocked,
                has_cat=item.has_cat,
                confidence=1.0,
                bbox_x=item.bbox_x if item.bbox_x is not None else (prior.bbox_x if prior else None),
                bbox_y=item.bbox_y if item.bbox_y is not None else (prior.bbox_y if prior else None),
                bbox_w=item.bbox_w if item.bbox_w is not None else (prior.bbox_w if prior else None),
                bbox_h=item.bbox_h if item.bbox_h is not None else (prior.bbox_h if prior else None),
            )
        )
    puzzle.rows = payload.rows
    puzzle.cols = payload.cols
    puzzle.rules_json = json.dumps(payload.rules.model_dump())
    puzzle.status = "confirmed"
    puzzle.needs_review = False
    puzzle.solver_status = None
    puzzle.solution_count = 0
    puzzle.solutions_truncated = False
    puzzle.solver_notes = None
    puzzle.solutions.clear()
    puzzle.updated_at = utcnow()
    db.commit()
    db.refresh(puzzle)
    return _board(puzzle)


def solve_puzzle(db: Session, user: User, puzzle_id: str) -> SolveResponse:
    settings = get_settings()
    puzzle = _owned(db, user, puzzle_id, load_cells=True)
    if not puzzle.cells or not puzzle.rows or not puzzle.cols:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirm a complete board before solving.")
    rules_model = _rules(puzzle)
    rules = RuleSet(**rules_model.model_dump())
    try:
        grid = _grid(puzzle)
    except HTTPException:
        raise
    result = solve_board(
        grid,
        rules=rules,
        limit=settings.solver_solution_limit,
        timeout_seconds=settings.solver_timeout_seconds,
    )
    puzzle.solutions.clear()
    db.flush()
    saved: list[PuzzleSolution] = []
    for index, placement in enumerate(result.solutions):
        errors = validate_solution(grid, placement, rules)
        if errors:
            logger.error("Rejected invalid solver output for %s: %s", puzzle.id, errors)
            continue
        solution = PuzzleSolution(
            puzzle_id=puzzle.id,
            solution_index=index,
            execution_time_ms=result.execution_time_ms,
            validation_passed=True,
            validation_errors=None,
        )
        for cat_index, (row, col) in enumerate(placement, start=1):
            cell = grid[row][col]
            solution.positions.append(
                SolutionPosition(
                    cat_index=cat_index,
                    row=row,
                    col=col,
                    color_id=cell.color_id,
                    color_label=_label_for(puzzle, row, col),
                    color_hex=_hex_for(puzzle, row, col),
                )
            )
        saved.append(solution)
        puzzle.solutions.append(solution)
    puzzle.solver_status = result.status
    puzzle.solution_count = len(saved)
    puzzle.solutions_truncated = result.truncated
    puzzle.processing_time_ms = result.execution_time_ms
    puzzle.solver_notes = "\n".join(result.conflicts) if result.conflicts else result.explanation
    if result.status in {"unique", "multiple"} and saved:
        puzzle.status = "solved"
    elif result.status == "none":
        puzzle.status = "no_solution"
    elif result.status == "timeout":
        puzzle.status = "timeout"
    else:
        puzzle.status = "failed"
    puzzle.updated_at = utcnow()
    db.commit()
    for solution in saved:
        db.refresh(solution)
    logger.info("Solved %s status=%s found=%s", puzzle.id, result.status, len(saved))
    return SolveResponse(
        puzzle_id=puzzle.id,
        status=result.status,
        unique=result.unique and len(saved) == 1,
        solutions_found=len(saved),
        truncated=result.truncated,
        timed_out=result.timed_out,
        execution_time_ms=result.execution_time_ms,
        explanation=result.explanation,
        conflicts=result.conflicts,
        solutions=[_solution_response(solution) for solution in saved],
    )


def list_solutions(db: Session, user: User, puzzle_id: str) -> list[SolutionResponse]:
    puzzle = _owned(db, user, puzzle_id, load_solutions=True)
    return [_solution_response(solution) for solution in puzzle.solutions]


def get_solution(db: Session, user: User, puzzle_id: str, solution_id: str) -> SolutionResponse:
    puzzle = _owned(db, user, puzzle_id, load_solutions=True)
    solution = next((item for item in puzzle.solutions if item.id == solution_id), None)
    if solution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solution not found.")
    return _solution_response(solution)


def puzzle_image(db: Session, user: User, puzzle_id: str) -> tuple[bytes, str]:
    puzzle = _owned(db, user, puzzle_id)
    relative = puzzle.normalized_image_path or puzzle.original_image_path
    data = read_bytes(relative)
    media = "image/png" if relative.endswith(".png") else "image/jpeg" if relative.endswith((".jpg", ".jpeg")) else "image/webp"
    return data, media


def solution_png(db: Session, user: User, puzzle_id: str, solution_id: str) -> bytes:
    puzzle = _owned(db, user, puzzle_id, load_cells=True, load_solutions=True)
    solution = next((item for item in puzzle.solutions if item.id == solution_id), None)
    if solution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solution not found.")
    rows = puzzle.rows or 0
    cols = puzzle.cols or 0
    colors = [[None for _ in range(cols)] for _ in range(rows)]
    boxes = [[None for _ in range(cols)] for _ in range(rows)]
    for cell in puzzle.cells:
        if cell.row < rows and cell.col < cols:
            colors[cell.row][cell.col] = cell.color_hex
            if None not in (cell.bbox_x, cell.bbox_y, cell.bbox_w, cell.bbox_h):
                boxes[cell.row][cell.col] = (cell.bbox_x, cell.bbox_y, cell.bbox_w, cell.bbox_h)
    background = None
    if puzzle.normalized_image_path:
        try:
            background = _load_bgr(puzzle.normalized_image_path)
        except HTTPException:
            background = None
    placements = [(position.row, position.col) for position in solution.positions]
    image = render_solution_image(
        rows=rows,
        cols=cols,
        color_hex=colors,
        placements=placements,
        background=background,
        boxes=boxes,
    )
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not render the solution image.")
    return encoded.tobytes()


def _owned(
    db: Session,
    user: User,
    puzzle_id: str,
    *,
    load_cells: bool = False,
    load_solutions: bool = False,
) -> Puzzle:
    stmt = select(Puzzle).where(Puzzle.id == puzzle_id, Puzzle.user_id == user.id)
    options = []
    if load_cells:
        options.append(selectinload(Puzzle.cells))
    if load_solutions:
        options.append(selectinload(Puzzle.solutions).selectinload(PuzzleSolution.positions))
    if options:
        stmt = stmt.options(*options)
    puzzle = db.scalar(stmt)
    if puzzle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Puzzle not found.")
    return puzzle


def _validate_board_payload(payload: BoardUpdate) -> None:
    expected = {(row, col) for row in range(payload.rows) for col in range(payload.cols)}
    seen = {(cell.row, cell.col) for cell in payload.cells}
    if seen != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The board must include every cell exactly once for the chosen dimensions.",
        )
    for cell in payload.cells:
        if cell.color_id is None or not cell.color_label or not cell.color_hex:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Row {cell.row + 1}, column {cell.col + 1} needs a color before it can be saved.",
            )


def _grid(puzzle: Puzzle) -> list[list[CellView]]:
    rows = puzzle.rows or 0
    cols = puzzle.cols or 0
    grid: list[list[CellView | None]] = [[None for _ in range(cols)] for _ in range(rows)]
    for cell in puzzle.cells:
        if not (0 <= cell.row < rows and 0 <= cell.col < cols):
            continue
        grid[cell.row][cell.col] = CellView(
            row=cell.row,
            col=cell.col,
            color_id=cell.color_id,
            blocked=cell.blocked,
            has_cat=cell.has_cat,
        )
    if any(cell is None for row in grid for cell in row):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The saved board is incomplete.")
    return grid  # type: ignore[return-value]


def _replace_cells_from_detection(puzzle: Puzzle, detected) -> None:
    puzzle.cells.clear()
    for cell in detected.cells:
        bbox = cell.bbox
        puzzle.cells.append(
            PuzzleCell(
                puzzle_id=puzzle.id,
                row=cell.row,
                col=cell.col,
                color_id=cell.color_id,
                color_label=cell.color_label,
                color_hex=cell.color_hex,
                blocked=cell.blocked,
                has_cat=cell.has_cat,
                confidence=cell.confidence,
                bbox_x=bbox[0] if bbox else None,
                bbox_y=bbox[1] if bbox else None,
                bbox_w=bbox[2] if bbox else None,
                bbox_h=bbox[3] if bbox else None,
            )
        )


def _load_bgr(relative_path: str) -> np.ndarray:
    data = read_bytes(relative_path)
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The stored image could not be read.")
    return image


def _write_png(relative_path: str, image: np.ndarray | None) -> None:
    if image is None:
        return
    ok, encoded = cv2.imencode(".png", image)
    if ok:
        save_bytes(relative_path, encoded.tobytes())


def _image_kind(data: bytes) -> str | None:
    if data.startswith(_PNG):
        return "png"
    if data.startswith(_JPEG):
        return "jpeg"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    return None


def _pillow_accepts(data: bytes) -> bool:
    from io import BytesIO

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def _rules(puzzle: Puzzle) -> RulesModel:
    try:
        return RulesModel.model_validate(json.loads(puzzle.rules_json))
    except (json.JSONDecodeError, ValueError):
        return RulesModel()


def _notes(puzzle: Puzzle) -> list[str]:
    if not puzzle.detection_notes:
        return []
    return [line for line in puzzle.detection_notes.splitlines() if line.strip()]


def _summary(puzzle: Puzzle) -> PuzzleSummary:
    return PuzzleSummary(
        id=puzzle.id,
        original_filename=puzzle.original_filename,
        status=puzzle.status,
        rows=puzzle.rows,
        cols=puzzle.cols,
        solver_status=puzzle.solver_status,
        solution_count=puzzle.solution_count,
        detection_confidence=puzzle.detection_confidence,
        processing_time_ms=puzzle.processing_time_ms,
        created_at=puzzle.created_at.isoformat(timespec="seconds"),
        updated_at=puzzle.updated_at.isoformat(timespec="seconds"),
    )


def _detail(puzzle: Puzzle) -> PuzzleDetail:
    base = _summary(puzzle).model_dump()
    return PuzzleDetail(**base, needs_review=puzzle.needs_review, rules=_rules(puzzle), notes=_notes(puzzle), solver_notes=puzzle.solver_notes)


def _board(puzzle: Puzzle) -> BoardResponse:
    return BoardResponse(
        puzzle_id=puzzle.id,
        rows=puzzle.rows,
        cols=puzzle.cols,
        rules=_rules(puzzle),
        cells=[
            CellResponse(
                row=cell.row,
                col=cell.col,
                color_id=cell.color_id,
                color_label=cell.color_label,
                color_hex=cell.color_hex,
                blocked=cell.blocked,
                has_cat=cell.has_cat,
                confidence=cell.confidence,
                bbox_x=cell.bbox_x,
                bbox_y=cell.bbox_y,
                bbox_w=cell.bbox_w,
                bbox_h=cell.bbox_h,
            )
            for cell in sorted(puzzle.cells, key=lambda item: (item.row, item.col))
        ],
        detection_confidence=puzzle.detection_confidence,
        needs_review=puzzle.needs_review,
        notes=_notes(puzzle),
        status=puzzle.status,
    )


def _solution_response(solution: PuzzleSolution) -> SolutionResponse:
    return SolutionResponse(
        id=solution.id,
        index=solution.solution_index,
        execution_time_ms=solution.execution_time_ms,
        validation_passed=solution.validation_passed,
        placements=[
            PlacementResponse(
                cat=position.cat_index,
                row=position.row,
                col=position.col,
                color_id=position.color_id,
                color_label=position.color_label,
                color_hex=position.color_hex,
            )
            for position in solution.positions
        ],
    )


def _label_for(puzzle: Puzzle, row: int, col: int) -> str | None:
    for cell in puzzle.cells:
        if cell.row == row and cell.col == col:
            return cell.color_label
    return None


def _hex_for(puzzle: Puzzle, row: int, col: int) -> str | None:
    for cell in puzzle.cells:
        if cell.row == row and cell.col == col:
            return cell.color_hex
    return None

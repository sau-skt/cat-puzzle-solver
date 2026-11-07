"""Puzzle API models."""

import re

from pydantic import BaseModel, Field, field_validator


class RulesModel(BaseModel):
    one_per_row: bool = True
    one_per_column: bool = True
    one_per_color: bool = True
    no_touching: bool = True


class CellModel(BaseModel):
    row: int = Field(ge=0, le=15)
    col: int = Field(ge=0, le=15)
    color_id: int | None = None
    color_label: str | None = Field(default=None, max_length=32)
    color_hex: str | None = None
    blocked: bool = False
    has_cat: bool = False
    confidence: float = 1.0
    bbox_x: int | None = None
    bbox_y: int | None = None
    bbox_w: int | None = None
    bbox_h: int | None = None

    @field_validator("color_hex")
    @classmethod
    def check_hex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError("Colors must use #RRGGBB.")
        return value.lower()


class BoardUpdate(BaseModel):
    rows: int = Field(ge=2, le=16)
    cols: int = Field(ge=2, le=16)
    cells: list[CellModel]
    rules: RulesModel = Field(default_factory=RulesModel)


class CellResponse(CellModel):
    pass


class BoardResponse(BaseModel):
    puzzle_id: str
    rows: int | None
    cols: int | None
    rules: RulesModel
    cells: list[CellResponse]
    detection_confidence: float | None
    needs_review: bool
    notes: list[str]
    status: str


class PlacementResponse(BaseModel):
    cat: int
    row: int
    col: int
    color_id: int | None
    color_label: str | None
    color_hex: str | None


class SolutionResponse(BaseModel):
    id: str
    index: int
    placements: list[PlacementResponse]
    validation_passed: bool
    execution_time_ms: float


class SolveResponse(BaseModel):
    puzzle_id: str
    status: str
    unique: bool
    solutions_found: int
    truncated: bool
    timed_out: bool
    execution_time_ms: float
    explanation: str | None
    conflicts: list[str]
    solutions: list[SolutionResponse]


class PuzzleSummary(BaseModel):
    id: str
    original_filename: str
    status: str
    rows: int | None
    cols: int | None
    solver_status: str | None
    solution_count: int
    detection_confidence: float | None
    processing_time_ms: float | None
    created_at: str
    updated_at: str


class PuzzleDetail(PuzzleSummary):
    needs_review: bool
    rules: RulesModel
    notes: list[str]
    solver_notes: str | None


class PuzzleListResponse(BaseModel):
    items: list[PuzzleSummary]
    total: int


class StatsResponse(BaseModel):
    total: int
    solved: int
    no_solution: int
    in_progress: int
    success_rate: float
    recent: list[PuzzleSummary]

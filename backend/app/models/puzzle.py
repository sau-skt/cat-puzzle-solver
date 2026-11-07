"""Puzzle, cell, solution, and placement tables."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.types import utcnow


class Puzzle(Base):
    __tablename__ = "puzzles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cols: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True, nullable=False)
    detection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    solver_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    solution_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    solutions_truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processing_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    solver_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="puzzles")
    cells: Mapped[list["PuzzleCell"]] = relationship(
        back_populates="puzzle", cascade="all, delete-orphan", order_by="PuzzleCell.row, PuzzleCell.col"
    )
    solutions: Mapped[list["PuzzleSolution"]] = relationship(
        back_populates="puzzle", cascade="all, delete-orphan", order_by="PuzzleSolution.solution_index"
    )


class PuzzleCell(Base):
    __tablename__ = "puzzle_cells"
    __table_args__ = (UniqueConstraint("puzzle_id", "row", "col", name="uq_puzzle_cell_position"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    puzzle_id: Mapped[str] = mapped_column(ForeignKey("puzzles.id", ondelete="CASCADE"), index=True, nullable=False)
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    col: Mapped[int] = mapped_column(Integer, nullable=False)
    color_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_cat: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bbox_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_w: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_h: Mapped[int | None] = mapped_column(Integer, nullable=True)

    puzzle: Mapped[Puzzle] = relationship(back_populates="cells")


class PuzzleSolution(Base):
    __tablename__ = "puzzle_solutions"
    __table_args__ = (UniqueConstraint("puzzle_id", "solution_index", name="uq_puzzle_solution_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    puzzle_id: Mapped[str] = mapped_column(ForeignKey("puzzles.id", ondelete="CASCADE"), index=True, nullable=False)
    solution_index: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    puzzle: Mapped[Puzzle] = relationship(back_populates="solutions")
    positions: Mapped[list["SolutionPosition"]] = relationship(
        back_populates="solution", cascade="all, delete-orphan", order_by="SolutionPosition.cat_index"
    )


class SolutionPosition(Base):
    __tablename__ = "solution_positions"
    __table_args__ = (UniqueConstraint("solution_id", "cat_index", name="uq_solution_cat_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    solution_id: Mapped[str] = mapped_column(
        ForeignKey("puzzle_solutions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cat_index: Mapped[int] = mapped_column(Integer, nullable=False)
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    col: Mapped[int] = mapped_column(Integer, nullable=False)
    color_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)

    solution: Mapped["PuzzleSolution"] = relationship(back_populates="positions")

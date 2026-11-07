"""Independent solution validator.

This module does not import the search engine. Callers must run it on every
candidate before treating that candidate as a solution.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CellView:
    row: int
    col: int
    color_id: int | None
    blocked: bool
    has_cat: bool = False


@dataclass(frozen=True)
class RuleSet:
    one_per_row: bool = True
    one_per_column: bool = True
    one_per_color: bool = True
    no_touching: bool = True

    def as_dict(self) -> dict[str, bool]:
        return {
            "one_per_row": self.one_per_row,
            "one_per_column": self.one_per_column,
            "one_per_color": self.one_per_color,
            "no_touching": self.no_touching,
        }


def validate_solution(
    grid: list[list[CellView]],
    placements: list[tuple[int, int]],
    rules: RuleSet | None = None,
) -> list[str]:
    """Return a list of human-readable violations. An empty list means valid."""
    rules = rules or RuleSet()
    errors: list[str] = []
    if not grid or not grid[0]:
        return ["The board is empty."]

    rows = len(grid)
    cols = len(grid[0])
    if any(len(row) != cols for row in grid):
        return ["The board is not rectangular."]

    seen: set[tuple[int, int]] = set()
    for row, col in placements:
        if not (0 <= row < rows and 0 <= col < cols):
            errors.append(f"Placement row {row + 1}, column {col + 1} is outside the board.")
            continue
        if (row, col) in seen:
            errors.append(f"More than one cat was placed on row {row + 1}, column {col + 1}.")
        seen.add((row, col))
        cell = grid[row][col]
        if cell.blocked:
            errors.append(f"A cat was placed on blocked cell row {row + 1}, column {col + 1}.")
        if cell.color_id is None:
            errors.append(f"A cat was placed on row {row + 1}, column {col + 1}, which has no color.")

    if rules.one_per_row:
        by_row: dict[int, int] = {}
        for row, _col in placements:
            if 0 <= row < rows:
                by_row[row] = by_row.get(row, 0) + 1
        for row in range(rows):
            count = by_row.get(row, 0)
            if count != 1:
                errors.append(f"Row {row + 1} has {count} cats; exactly one is required.")

    if rules.one_per_column:
        by_col: dict[int, int] = {}
        for _row, col in placements:
            if 0 <= col < cols:
                by_col[col] = by_col.get(col, 0) + 1
        for col in range(cols):
            count = by_col.get(col, 0)
            if count != 1:
                errors.append(f"Column {col + 1} has {count} cats; exactly one is required.")

    if rules.one_per_color:
        colors_on_board = {
            cell.color_id
            for row in grid
            for cell in row
            if cell.color_id is not None
        }
        used: dict[int, int] = {}
        for row, col in placements:
            if 0 <= row < rows and 0 <= col < cols and grid[row][col].color_id is not None:
                color = grid[row][col].color_id
                assert color is not None
                used[color] = used.get(color, 0) + 1
        for color, count in sorted(used.items()):
            if count != 1:
                errors.append(f"Color {color} is used by {count} cats; exactly one is required.")
        missing = sorted(color for color in colors_on_board if color not in used)
        for color in missing:
            errors.append(f"Color {color} has no cat.")

    if rules.no_touching:
        for index, (row, col) in enumerate(placements):
            for other_row, other_col in placements[index + 1 :]:
                if max(abs(row - other_row), abs(col - other_col)) <= 1:
                    errors.append(
                        "Cats on "
                        f"row {row + 1} column {col + 1} and "
                        f"row {other_row + 1} column {other_col + 1} touch, including diagonally."
                    )
    return errors

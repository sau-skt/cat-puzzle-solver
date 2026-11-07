"""Deterministic cat-placement solver.

The search places exactly one cat per row on a square board. Column uniqueness,
color uniqueness, and king-separation (no orthogonal or diagonal contact) are
enforced with forward checking and singleton propagation. The next row is chosen
with the minimum-remaining-values heuristic. Every accepted placement is checked
by the separate validator before it is returned.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.solver.validate import CellView, RuleSet, validate_solution


@dataclass
class SolveResult:
    status: str
    unique: bool
    solutions: list[list[tuple[int, int]]]
    truncated: bool
    timed_out: bool
    execution_time_ms: float
    conflicts: list[str] = field(default_factory=list)
    explanation: str | None = None


def solve_board(
    grid: list[list[CellView]],
    *,
    rules: RuleSet | None = None,
    limit: int = 20,
    timeout_seconds: float = 10.0,
) -> SolveResult:
    started = time.perf_counter()
    rules = rules or RuleSet()
    limit = max(1, limit)

    def finish(
        status: str,
        solutions: list[list[tuple[int, int]]] | None = None,
        *,
        unique: bool = False,
        truncated: bool = False,
        timed_out: bool = False,
        conflicts: list[str] | None = None,
        explanation: str | None = None,
    ) -> SolveResult:
        elapsed = (time.perf_counter() - started) * 1000
        return SolveResult(
            status=status,
            unique=unique,
            solutions=solutions or [],
            truncated=truncated,
            timed_out=timed_out,
            execution_time_ms=elapsed,
            conflicts=conflicts or [],
            explanation=explanation,
        )

    structural = _structural_problems(grid, rules)
    if structural:
        return finish("none", conflicts=structural, explanation=structural[0])

    rows = len(grid)
    colors = _colors(grid)
    conflicts = _preplaced_conflicts(grid, rules, colors)
    if conflicts:
        return finish("none", conflicts=conflicts, explanation=conflicts[0])

    domains = _initial_domains(grid)
    assigned: dict[int, int] = {}
    used: set[int] = set()

    for row in range(rows):
        placed = [col for col in range(rows) if grid[row][col].has_cat]
        if len(placed) == 1:
            col = placed[0]
            domains[row] = {col}

    propagated = _propagate(grid, domains, assigned, used, rules, colors)
    if propagated is None:
        conflicts = _diagnose(grid, rules, colors)
        return finish("none", conflicts=conflicts, explanation=conflicts[0] if conflicts else "The constraints conflict.")

    solutions: list[list[tuple[int, int]]] = []
    state = {"timed_out": False, "truncated": False}
    deadline = time.perf_counter() + timeout_seconds

    def search(current_domains: list[set[int]], current_assigned: dict[int, int], current_used: set[int]) -> None:
        if state["timed_out"] or len(solutions) >= limit:
            return
        if time.perf_counter() > deadline:
            state["timed_out"] = True
            return
        if len(current_assigned) == rows:
            placement = [(row, current_assigned[row]) for row in range(rows)]
            errors = validate_solution(grid, placement, rules)
            if errors:
                raise RuntimeError("Solver produced a placement the validator rejected: " + "; ".join(errors))
            solutions.append(placement)
            return

        row = min(
            (candidate for candidate in range(rows) if candidate not in current_assigned),
            key=lambda candidate: (len(current_domains[candidate]), candidate),
        )
        ordered = sorted(
            current_domains[row],
            key=lambda col: _lcv(grid, current_domains, row, col, current_used, rules),
        )
        for col in ordered:
            if state["timed_out"] or len(solutions) >= limit:
                return
            next_domains = [set(values) for values in current_domains]
            next_assigned = dict(current_assigned)
            next_used = set(current_used)
            next_domains[row] = {col}
            if not _eliminate(grid, next_domains, row, col, rules):
                continue
            color = grid[row][col].color_id
            if rules.one_per_color and color in next_used:
                continue
            next_assigned[row] = col
            if color is not None:
                next_used.add(color)
            if _propagate(grid, next_domains, next_assigned, next_used, rules, colors) is None:
                continue
            search(next_domains, next_assigned, next_used)

    search(domains, assigned, used)

    if state["timed_out"] and not solutions:
        return finish(
            "timeout",
            timed_out=True,
            explanation="The solver stopped because it reached the time limit before deciding.",
            conflicts=["Search timed out before a complete scan of the remaining candidates."],
        )

    truncated = len(solutions) >= limit or state["timed_out"]
    if not solutions:
        conflicts = _diagnose(grid, rules, colors)
        return finish("none", conflicts=conflicts, explanation=conflicts[0] if conflicts else "No solution exists.")

    if len(solutions) == 1 and not truncated:
        status = "unique"
        unique = True
    else:
        status = "multiple"
        unique = False
    explanation = None
    if truncated and not state["timed_out"]:
        explanation = f"Showing the first {len(solutions)} solutions. The search stopped at the configured limit."
    elif state["timed_out"]:
        explanation = "The search reached the time limit. More solutions may exist."
    return finish(status, solutions, unique=unique, truncated=truncated, timed_out=state["timed_out"], explanation=explanation)


def _colors(grid: list[list[CellView]]) -> set[int]:
    return {cell.color_id for row in grid for cell in row if cell.color_id is not None}


def _structural_problems(grid: list[list[CellView]], rules: RuleSet) -> list[str]:
    if not grid or not grid[0]:
        return ["The board has no cells."]
    rows = len(grid)
    cols = len(grid[0])
    if any(len(row) != cols for row in grid):
        return ["Every row must contain the same number of cells."]
    if rows != cols:
        return [
            f"The detected board is {rows}×{cols}. One cat per row and one cat per column requires a square board. Correct the dimensions and try again."
        ]
    if rows < 1:
        return ["The board is empty."]
    if rows > 16:
        return ["Boards larger than 16×16 are rejected. Correct the dimensions if the grid was misread."]
    unknown = [
        f"Row {cell.row + 1}, column {cell.col + 1} has no recognized color."
        for row in grid
        for cell in row
        if cell.color_id is None
    ]
    if unknown:
        return unknown[:8]
    if rules.one_per_row and rules.one_per_column and rows != cols:
        return ["One cat per row and per column is impossible when the board is not square."]
    colors = _colors(grid)
    if rules.one_per_color and len(colors) != rows:
        return [
            f"The board has {len(colors)} colors and {rows} rows. Exactly one cat per color requires the same count. Merge or split colors in the editor."
        ]
    return []


def _preplaced_conflicts(grid: list[list[CellView]], rules: RuleSet, colors: set[int]) -> list[str]:
    rows = len(grid)
    conflicts: list[str] = []
    placed: list[tuple[int, int]] = []
    for row in range(rows):
        cats = [col for col in range(rows) if grid[row][col].has_cat]
        if len(cats) > 1:
            conflicts.append(f"Row {row + 1} already has more than one cat.")
        for col in cats:
            if grid[row][col].blocked:
                conflicts.append(f"Row {row + 1}, column {col + 1} is marked both blocked and occupied by a cat.")
            placed.append((row, col))
    if rules.one_per_column:
        columns = [col for _row, col in placed]
        if len(columns) != len(set(columns)):
            conflicts.append("Existing cats share a column.")
    if rules.one_per_color:
        used = [grid[row][col].color_id for row, col in placed]
        if any(color is None for color in used) or len(used) != len(set(used)):
            conflicts.append("Existing cats do not have distinct colors.")
    if rules.no_touching:
        for index, (row, col) in enumerate(placed):
            for other_row, other_col in placed[index + 1 :]:
                if max(abs(row - other_row), abs(col - other_col)) <= 1:
                    conflicts.append(
                        f"Existing cats on row {row + 1} column {col + 1} and row {other_row + 1} column {other_col + 1} touch."
                    )
    for row in range(rows):
        if not any(not grid[row][col].blocked for col in range(rows)):
            conflicts.append(f"Row {row + 1} is entirely blocked, so it cannot hold a cat.")
    for col in range(rows):
        if not any(not grid[row][col].blocked for row in range(rows)):
            conflicts.append(f"Column {col + 1} is entirely blocked, so it cannot hold a cat.")
    if rules.one_per_color:
        for color in sorted(colors):
            available = [
                (row, col)
                for row in range(rows)
                for col in range(rows)
                if grid[row][col].color_id == color and not grid[row][col].blocked
            ]
            if not available:
                conflicts.append(f"Color {color} only appears on blocked cells, so it cannot receive a cat.")
    return conflicts


def _initial_domains(grid: list[list[CellView]]) -> list[set[int]]:
    rows = len(grid)
    domains: list[set[int]] = []
    for row in range(rows):
        domains.append(
            {
                col
                for col in range(rows)
                if not grid[row][col].blocked and grid[row][col].color_id is not None
            }
        )
    return domains


def _touches(row: int, col: int, other_row: int, other_col: int) -> bool:
    return max(abs(row - other_row), abs(col - other_col)) <= 1


def _eliminate(
    grid: list[list[CellView]],
    domains: list[set[int]],
    row: int,
    col: int,
    rules: RuleSet,
) -> bool:
    color = grid[row][col].color_id
    size = len(grid)
    for other_row in range(size):
        if other_row == row:
            continue
        remove = []
        for other_col in domains[other_row]:
            if rules.one_per_column and other_col == col:
                remove.append(other_col)
            elif rules.no_touching and _touches(row, col, other_row, other_col):
                remove.append(other_col)
            elif rules.one_per_color and color is not None and grid[other_row][other_col].color_id == color:
                remove.append(other_col)
        for other_col in remove:
            domains[other_row].discard(other_col)
        if not domains[other_row]:
            return False
    return True


def _propagate(
    grid: list[list[CellView]],
    domains: list[set[int]],
    assigned: dict[int, int],
    used: set[int],
    rules: RuleSet,
    colors: set[int],
) -> list[set[int]] | None:
    size = len(grid)
    changed = True
    while changed:
        changed = False
        for row in range(size):
            if row in assigned:
                continue
            if not domains[row]:
                return None
            if len(domains[row]) == 1:
                col = next(iter(domains[row]))
                color = grid[row][col].color_id
                if rules.one_per_color and color in used:
                    return None
                if not _eliminate(grid, domains, row, col, rules):
                    return None
                assigned[row] = col
                if color is not None:
                    used.add(color)
                changed = True
        if rules.one_per_color:
            for color in colors:
                if color in used:
                    continue
                options: list[tuple[int, int]] = []
                for row in range(size):
                    if row in assigned:
                        if grid[row][assigned[row]].color_id == color:
                            options.append((row, assigned[row]))
                        continue
                    for col in domains[row]:
                        if grid[row][col].color_id == color:
                            options.append((row, col))
                open_options = [(row, col) for row, col in options if row not in assigned]
                if not options:
                    return None
                if len(open_options) == 1 and len(options) == 1:
                    row, col = open_options[0]
                    if col not in domains[row]:
                        return None
                    if domains[row] != {col}:
                        domains[row] = {col}
                        changed = True
    if rules.one_per_color:
        for color in colors:
            if color in used:
                continue
            if not any(
                grid[row][col].color_id == color
                for row in range(size)
                if row not in assigned
                for col in domains[row]
            ):
                return None
    return domains


def _lcv(
    grid: list[list[CellView]],
    domains: list[set[int]],
    row: int,
    col: int,
    used: set[int],
    rules: RuleSet,
) -> tuple[int, int]:
    """Least-constraining value: prefer the column that removes fewer candidates."""
    removed = 0
    color = grid[row][col].color_id
    for other_row, values in enumerate(domains):
        if other_row == row:
            continue
        for other_col in values:
            if rules.one_per_column and other_col == col:
                removed += 1
            elif rules.no_touching and _touches(row, col, other_row, other_col):
                removed += 1
            elif rules.one_per_color and color is not None and color not in used and grid[other_row][other_col].color_id == color:
                removed += 1
    return (removed, col)


def _diagnose(grid: list[list[CellView]], rules: RuleSet, colors: set[int]) -> list[str]:
    direct = _preplaced_conflicts(grid, rules, colors)
    if direct:
        return direct
    rows = len(grid)
    notes: list[str] = []
    domains = _initial_domains(grid)
    for row, values in enumerate(domains):
        if not values:
            notes.append(f"Row {row + 1} has no open cell after blocked cells are removed.")
    if rules.one_per_color:
        for color in sorted(colors):
            spots = [
                (row, col)
                for row in range(rows)
                for col in range(rows)
                if grid[row][col].color_id == color and not grid[row][col].blocked
            ]
            if len(spots) == 0:
                notes.append(f"Color {color} has no open cell.")
    if not notes:
        notes.append(
            "No placement satisfies the rules together. The conflict is between column uniqueness, color uniqueness, and the rule that cats cannot touch, including diagonally."
        )
    return notes

"""Solver tests against an independent brute-force enumerator."""

import random

from app.solver.engine import solve_board
from app.solver.validate import CellView, RuleSet, validate_solution


def grid_from(colors, blocked=(), cats=()):
    size = len(colors)
    return [
        [
            CellView(
                row=row,
                col=col,
                color_id=colors[row][col],
                blocked=(row, col) in blocked,
                has_cat=(row, col) in cats,
            )
            for col in range(size)
        ]
        for row in range(size)
    ]


def brute(grid, rules=None):
    rules = rules or RuleSet()
    size = len(grid)
    found = []

    def walk(row, used_cols, used_colors, placed):
        if row == size:
            found.append(list(placed))
            return
        forced = [col for col in range(size) if grid[row][col].has_cat]
        candidates = forced or range(size)
        for col in candidates:
            cell = grid[row][col]
            if cell.blocked or cell.color_id is None:
                continue
            if rules.one_per_column and col in used_cols:
                continue
            if rules.one_per_color and cell.color_id in used_colors:
                continue
            if rules.no_touching and any(max(abs(row - prev_row), abs(col - prev_col)) <= 1 for prev_row, prev_col in placed):
                continue
            walk(
                row + 1,
                used_cols | {col},
                used_colors | {cell.color_id},
                placed + [(row, col)],
            )

    walk(0, set(), set(), [])
    return found


def assert_matches_brute(grid, rules=None):
    rules = rules or RuleSet()
    expected = {tuple(item) for item in brute(grid, rules)}
    result = solve_board(grid, rules=rules, limit=50, timeout_seconds=5)
    actual = {tuple(item) for item in result.solutions}
    assert not result.timed_out
    assert actual == expected
    if len(expected) == 0:
        assert result.status == "none"
        assert result.conflicts
    elif len(expected) == 1:
        assert result.status == "unique"
        assert result.unique
    else:
        assert result.status == "multiple"
        assert not result.unique


def test_multiple_solutions_on_open_board():
    colors = [[col for col in range(4)] for _ in range(4)]
    assert_matches_brute(grid_from(colors))


def test_blocked_cells_and_unique_solution():
    colors = [[col for col in range(4)] for _ in range(4)]
    blocked = {(0, 0), (0, 1), (1, 0), (1, 1), (2, 2), (2, 3), (3, 2)}
    # Leave a narrow set of openings and compare with brute force.
    grid = grid_from(colors, blocked=blocked)
    assert_matches_brute(grid)
    result = solve_board(grid, limit=10)
    for solution in result.solutions:
        assert all(cell not in blocked for cell in solution)
        assert validate_solution(grid, solution) == []


def test_no_solution_when_a_row_is_blocked():
    colors = [[col for col in range(4)] for _ in range(4)]
    blocked = {(0, col) for col in range(4)}
    result = solve_board(grid_from(colors, blocked=blocked))
    assert result.status == "none"
    assert result.solutions == []
    assert any("Row 1" in note and "blocked" in note for note in result.conflicts)


def test_preplaced_cats_force_the_known_solution():
    size = 5
    columns = [(2 * row) % size for row in range(size)]
    colors = [[col for col in range(size)] for _ in range(size)]
    cats = [(row, columns[row]) for row in range(size)]
    grid = grid_from(colors, cats=cats)
    result = solve_board(grid)
    assert result.status == "unique"
    assert result.solutions == [cats]
    assert validate_solution(grid, result.solutions[0]) == []


def test_adjacent_preplaced_cats_conflict():
    colors = [[col for col in range(4)] for _ in range(4)]
    result = solve_board(grid_from(colors, cats=[(0, 0), (1, 1)]))
    assert result.status == "none"
    assert any("touch" in note for note in result.conflicts)


def test_validator_rejects_each_broken_constraint():
    colors = [[col for col in range(3)] for _ in range(3)]
    grid = grid_from(colors, blocked={(0, 2)})
    assert any("Row" in error for error in validate_solution(grid, [(0, 0), (1, 1)]))
    assert any("blocked" in error for error in validate_solution(grid, [(0, 2), (1, 0), (2, 1)]))
    same_column = [(0, 0), (1, 0), (2, 1)]
    assert any("Column" in error for error in validate_solution(grid, same_column))
    touching = [(0, 0), (1, 1), (2, 0)]
    # Columns are not unique either; the touching error must still be reported.
    assert any("touch" in error for error in validate_solution(grid, [(0, 0), (1, 1), (2, 0)]))
    duplicate_color = grid_from([[0, 1, 2], [0, 1, 2], [0, 1, 2]])
    assert any("Color" in error for error in validate_solution(duplicate_color, [(0, 0), (1, 0), (2, 1)]))


def test_random_boards_match_independent_search():
    rng = random.Random(7)
    for size in (3, 4):
        for _ in range(8):
            colors = [[(row * 2 + col) % size for col in range(size)] for row in range(size)]
            blocked = {
                (row, col)
                for row in range(size)
                for col in range(size)
                if rng.random() < 0.15
            }
            assert_matches_brute(grid_from(colors, blocked=blocked))


def test_larger_boards_return_validated_solutions():
    for size, step in ((8, 3), (10, 3)):
        colors = [[col for col in range(size)] for _ in range(size)]
        known = [(row, (step * row) % size) for row in range(size)]
        assert all(abs(known[i][1] - known[i + 1][1]) >= 2 for i in range(size - 1))
        grid = grid_from(colors)
        assert validate_solution(grid, known) == []
        result = solve_board(grid, limit=5, timeout_seconds=5)
        assert result.status in {"unique", "multiple"}
        assert result.solutions
        for solution in result.solutions:
            assert validate_solution(grid, solution) == []


def test_color_count_mismatch_is_reported_not_invented():
    colors = [[0 for _ in range(4)] for _ in range(4)]
    result = solve_board(grid_from(colors))
    assert result.status == "none"
    assert result.solutions == []
    assert any("color" in note.lower() for note in result.conflicts)


def test_rectangular_board_is_rejected():
    grid = [
        [CellView(0, 0, 0, False), CellView(0, 1, 1, False), CellView(0, 2, 2, False)],
        [CellView(1, 0, 1, False), CellView(1, 1, 2, False), CellView(1, 2, 0, False)],
    ]
    result = solve_board(grid)
    assert result.status == "none"
    assert result.solutions == []
    assert any("square" in note.lower() for note in result.conflicts)


def test_turning_off_touching_allows_neighbors():
    colors = [[col for col in range(3)] for _ in range(3)]
    rules = RuleSet(no_touching=False)
    with_gap = solve_board(grid_from(colors), rules=RuleSet(), limit=30)
    without_gap = solve_board(grid_from(colors), rules=rules, limit=30)
    assert len(without_gap.solutions) > len(with_gap.solutions)
    assert any(max(abs(a[0] - b[0]), abs(a[1] - b[1])) <= 1 for solution in without_gap.solutions for a in solution for b in solution if a < b)

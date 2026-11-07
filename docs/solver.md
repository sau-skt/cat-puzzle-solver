# Puzzle solver

The game asks for a square board: one cat in every row, every column, and every color, with no two cats touching even diagonally, and no cat on an X.

## Search

Each row is a variable. Its domain is the set of columns that are not blocked and have a color.

1. Fixed cats from the screenshot are assigned first.
2. Constraint propagation assigns any row whose domain has shrunk to one column, then checks that every unused color still has a home.
3. Backtracking picks the unassigned row with the fewest remaining columns (minimum remaining values).
4. Columns are tried in least-constraining order.
5. Forward checking removes the used column, neighboring cells, and the used color from the other rows. An empty domain ends that branch.
6. The search stops at the configured solution limit or time limit. A timeout is reported as a timeout, not as “no solution.”

## Independent validation

`app/solver/validate.py` does not import the search. Before a placement is stored, the validator checks:

- one cat in each row
- one cat in each column
- one cat of each color
- Chebyshev distance greater than 1 between every pair
- no blocked cell

If the validator disagrees with the search, that placement is dropped and the error is logged.

## Outcomes

- **unique** — the search finished and found one valid placement
- **multiple** — more than one valid placement, or the limit was reached
- **none** — the search finished with zero placements, with a short explanation of the conflict
- **timeout** — time ran out before a decision

The default limit is 20 solutions and 10 seconds. Both are environment settings.

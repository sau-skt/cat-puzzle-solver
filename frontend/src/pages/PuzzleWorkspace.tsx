import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PuzzleGrid } from "../components/PuzzleGrid";
import { Alert, Button } from "../components/ui";
import { api, errorMessage } from "../services/api";
import type { Board, Cell, PuzzleDetail, Rules, SolveResult } from "../types";
import { solutionInstructions } from "../utils/solutionText";

const PRESETS = [
  { id: 0, label: "red", hex: "#d24a4a" },
  { id: 1, label: "orange", hex: "#e0892d" },
  { id: 2, label: "yellow", hex: "#e6c84a" },
  { id: 3, label: "green", hex: "#3e7a5a" },
  { id: 4, label: "cyan", hex: "#3aa8b5" },
  { id: 5, label: "blue", hex: "#3c6fbf" },
  { id: 6, label: "purple", hex: "#8a4fbf" },
  { id: 7, label: "pink", hex: "#e07aa8" },
  { id: 8, label: "brown", hex: "#8a5a3c" },
  { id: 9, label: "lime", hex: "#7dba6a" },
];

const DEFAULT_RULES: Rules = {
  one_per_row: true,
  one_per_column: true,
  one_per_color: true,
  no_touching: true,
};

export function PuzzleWorkspace() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const started = useRef(false);
  const [cells, setCells] = useState<Cell[] | null>(null);
  const [rows, setRows] = useState(10);
  const [cols, setCols] = useState(10);
  const [rules, setRules] = useState<Rules>(DEFAULT_RULES);
  const [selected, setSelected] = useState<{ row: number; col: number } | null>(null);
  const [result, setResult] = useState<SolveResult | null>(null);
  const [active, setActive] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const puzzle = useQuery({
    queryKey: ["puzzle", id],
    queryFn: async () => (await api.get<PuzzleDetail>(`/puzzles/${id}`)).data,
  });
  const board = useQuery({
    queryKey: ["board", id],
    queryFn: async () => (await api.get<Board>(`/puzzles/${id}/board`)).data,
    enabled: puzzle.data?.status !== "uploaded",
  });

  useEffect(() => {
    if (puzzle.data?.status !== "uploaded" || started.current) return;
    started.current = true;
    setBusy("Reading the screenshot…");
    api
      .post<Board>(`/puzzles/${id}/analyze`)
      .then((response) => {
        applyBoard(response.data);
        queryClient.setQueryData(["board", id], response.data);
        queryClient.invalidateQueries({ queryKey: ["puzzle", id] });
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setBusy(""));
  }, [puzzle.data?.status, id, queryClient]);

  useEffect(() => {
    if (board.data && !cells) applyBoard(board.data);
  }, [board.data, cells]);

  useEffect(() => {
    if (puzzle.data?.status !== "solved" || result) return;
    api.get<SolveResult["solutions"]>(`/puzzles/${id}/solutions`).then((response) => {
      if (response.data.length) {
        setResult({
          puzzle_id: id,
          status: puzzle.data?.solver_status || "multiple",
          unique: response.data.length === 1,
          solutions_found: response.data.length,
          truncated: false,
          timed_out: false,
          execution_time_ms: puzzle.data?.processing_time_ms || 0,
          explanation: puzzle.data?.solver_notes ?? null,
          conflicts: [],
          solutions: response.data,
        });
      }
    });
  }, [puzzle.data, id, result]);

  function applyBoard(next: Board) {
    setCells(next.cells);
    setRows(next.rows || 10);
    setCols(next.cols || 10);
    setRules(next.rules);
    setMessage(next.notes.join(" "));
  }

  const palette = useMemo(() => {
    const map = new Map<number, { id: number; label: string; hex: string }>();
    for (const cell of cells || []) {
      if (cell.color_id !== null && cell.color_hex && cell.color_label) {
        map.set(cell.color_id, { id: cell.color_id, label: cell.color_label, hex: cell.color_hex });
      }
    }
    return map.size ? [...map.values()] : PRESETS.slice(0, Math.max(rows, 2));
  }, [cells, rows]);

  function updateCell(row: number, col: number, patch: Partial<Cell>) {
    setCells((current) => current?.map((cell) => (cell.row === row && cell.col === col ? { ...cell, ...patch } : cell)) ?? null);
  }

  function rebuild(nextRows: number, nextCols: number) {
    const source = cells || [];
    const fallback = palette[0] || PRESETS[0];
    const next: Cell[] = [];
    for (let row = 0; row < nextRows; row += 1) {
      for (let col = 0; col < nextCols; col += 1) {
        const existing = source.find((cell) => cell.row === row && cell.col === col);
        next.push(
          existing || {
            row,
            col,
            color_id: fallback.id,
            color_label: fallback.label,
            color_hex: fallback.hex,
            blocked: false,
            has_cat: false,
            confidence: 1,
          },
        );
      }
    }
    setRows(nextRows);
    setCols(nextCols);
    setCells(next);
    setMessage("New cells use the first color. Review them before solving.");
  }

  async function solve() {
    if (!cells) return;
    setError("");
    setBusy("Solving…");
    try {
      await api.put(`/puzzles/${id}/board`, { rows, cols, rules, cells });
      const response = await api.post<SolveResult>(`/puzzles/${id}/solve`);
      setResult(response.data);
      setActive(0);
      queryClient.invalidateQueries({ queryKey: ["puzzle", id] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      if (!response.data.solutions.length) {
        setError(response.data.conflicts.join(" ") || response.data.explanation || "No solution was found.");
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy("");
    }
  }

  async function reanalyze() {
    setBusy("Reading the screenshot again…");
    setResult(null);
    setError("");
    try {
      const response = await api.post<Board>(`/puzzles/${id}/analyze`);
      applyBoard(response.data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy("");
    }
  }

  async function copySolution() {
    if (!result?.solutions[active]) return;
    await navigator.clipboard.writeText(solutionInstructions(result.solutions[active], result.solutions.length));
    setMessage("Placement instructions copied.");
  }

  async function downloadSolution() {
    if (!result?.solutions[active]) return;
    const response = await api.get(`/puzzles/${id}/solutions/${result.solutions[active].id}/image`, { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `cat-solution-${active + 1}.png`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const selectedCell = cells?.find((cell) => cell.row === selected?.row && cell.col === selected?.col) || null;
  const solution = result?.solutions[active];

  if (puzzle.isLoading || busy) {
    return <p className="text-ink/70">{busy || "Opening puzzle…"}</p>;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link to="/history" className="text-sm text-ink/60">
            History
          </Link>
          <h1 className="font-display text-4xl">{puzzle.data?.original_filename || "Puzzle"}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={reanalyze}>
            Read image again
          </Button>
          <Button onClick={solve}>Confirm and solve</Button>
        </div>
      </div>
      {error ? <Alert>{error}</Alert> : null}
      {message ? <Alert kind={board.data?.needs_review ? "warn" : "ok"}>{message}</Alert> : null}
      {board.data?.needs_review ? (
        <Alert kind="warn">Detection confidence is low. Correct the grid before solving. Nothing was invented for missing cells.</Alert>
      ) : null}

      {!cells?.length ? (
        <section className="rounded-3xl border border-line bg-paper p-5">
          <h2 className="font-display text-2xl">Build the board manually</h2>
          <p className="mt-1 text-sm text-ink/70">The screenshot did not produce a grid. Choose a size, then paint the cells.</p>
          <div className="mt-3 flex gap-3">
            <label className="text-sm">
              Rows
              <input className="ml-2 w-16 rounded-xl border border-line px-2 py-1" type="number" min={2} max={16} value={rows} onChange={(e) => setRows(Number(e.target.value))} />
            </label>
            <label className="text-sm">
              Columns
              <input className="ml-2 w-16 rounded-xl border border-line px-2 py-1" type="number" min={2} max={16} value={cols} onChange={(e) => setCols(Number(e.target.value))} />
            </label>
            <Button onClick={() => rebuild(rows, cols)}>Create grid</Button>
          </div>
        </section>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[auto_300px]">
          <section className="space-y-4">
            <PuzzleGrid
              rows={rows}
              cols={cols}
              cells={cells}
              selected={selected}
              placements={solution?.placements || []}
              onSelect={(cell) => setSelected({ row: cell.row, col: cell.col })}
            />
            <img
              src={`/api/puzzles/${id}/image`}
              alt="Uploaded puzzle"
              className="max-h-72 rounded-3xl border border-line bg-paper object-contain"
            />
          </section>
          <aside className="space-y-4 rounded-3xl border border-line bg-paper p-4">
            <h2 className="font-display text-2xl">{selectedCell ? `Row ${selectedCell.row + 1}, column ${selectedCell.col + 1}` : "Cell editor"}</h2>
            {selectedCell ? (
              <div className="space-y-3 text-sm">
                <p>Confidence {Math.round(selectedCell.confidence * 100)}%</p>
                <div className="flex flex-wrap gap-2">
                  {palette.map((color) => (
                    <button
                      key={color.id}
                      aria-label={color.label}
                      className="h-8 w-8 rounded-full border border-black/10"
                      style={{ background: color.hex, outline: selectedCell.color_id === color.id ? "2px solid #1c1612" : undefined }}
                      onClick={() =>
                        updateCell(selectedCell.row, selectedCell.col, {
                          color_id: color.id,
                          color_label: color.label,
                          color_hex: color.hex,
                        })
                      }
                    />
                  ))}
                </div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedCell.blocked}
                    onChange={(event) => updateCell(selectedCell.row, selectedCell.col, { blocked: event.target.checked })}
                  />
                  Blocked with an X
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedCell.has_cat}
                    onChange={(event) => updateCell(selectedCell.row, selectedCell.col, { has_cat: event.target.checked })}
                  />
                  Cat already placed
                </label>
              </div>
            ) : (
              <p className="text-sm text-ink/60">Select a cell to change its color, X mark, or existing cat.</p>
            )}
            <div className="space-y-2 border-t border-line pt-3 text-sm">
              <p className="font-semibold">Rules</p>
              {(
                [
                  ["one_per_row", "One cat per row"],
                  ["one_per_column", "One cat per column"],
                  ["one_per_color", "One cat per color"],
                  ["no_touching", "Cats cannot touch, even diagonally"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2">
                  <input type="checkbox" checked={rules[key]} onChange={(event) => setRules({ ...rules, [key]: event.target.checked })} />
                  {label}
                </label>
              ))}
            </div>
            <div className="flex items-end gap-2 border-t border-line pt-3 text-sm">
              <label>
                Rows
                <input className="mt-1 block w-16 rounded-xl border border-line px-2 py-1" type="number" min={2} max={16} value={rows} onChange={(e) => setRows(Number(e.target.value))} />
              </label>
              <label>
                Columns
                <input className="mt-1 block w-16 rounded-xl border border-line px-2 py-1" type="number" min={2} max={16} value={cols} onChange={(e) => setCols(Number(e.target.value))} />
              </label>
              <Button variant="ghost" onClick={() => rebuild(rows, cols)}>
                Apply size
              </Button>
            </div>
          </aside>
        </div>
      )}

      {result ? (
        <section className="rounded-3xl border border-line bg-paper p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-display text-3xl">
                {result.status === "unique" ? "Unique solution" : result.status === "multiple" ? "Multiple solutions" : "No solution"}
              </h2>
              <p className="text-sm text-ink/60">
                {result.solutions_found} shown · {result.execution_time_ms.toFixed(1)} ms
                {result.truncated ? " · search stopped at the solution limit" : ""}
                {result.timed_out ? " · timed out" : ""}
              </p>
            </div>
            {solution ? (
              <div className="flex gap-2">
                <Button variant="ghost" onClick={copySolution}>
                  Copy instructions
                </Button>
                <Button variant="ghost" onClick={downloadSolution}>
                  Download image
                </Button>
              </div>
            ) : null}
          </div>
          {result.solutions.length > 1 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {result.solutions.map((item, index) => (
                <button
                  key={item.id}
                  className={`rounded-full px-3 py-1 text-sm ${index === active ? "bg-ink text-cream" : "bg-cream"}`}
                  onClick={() => setActive(index)}
                >
                  Solution {index + 1}
                </button>
              ))}
            </div>
          ) : null}
          {solution ? (
            <div className="mt-4 grid gap-4 lg:grid-cols-[280px_1fr]">
              <img
                src={`/api/puzzles/${id}/solutions/${solution.id}/image`}
                alt="Solution drawn on the puzzle"
                className="w-full rounded-2xl border border-line"
              />
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="text-ink/50">
                      <th className="py-2">Cat</th>
                      <th>Row</th>
                      <th>Column</th>
                      <th>Color</th>
                    </tr>
                  </thead>
                  <tbody>
                    {solution.placements.map((place) => (
                      <tr key={place.cat} className="border-t border-line">
                        <td className="py-2">{place.cat}</td>
                        <td>{place.row + 1}</td>
                        <td>{place.col + 1}</td>
                        <td>
                          <span className="mr-2 inline-block h-3 w-3 rounded-full" style={{ background: place.color_hex || "#ccc" }} />
                          {place.color_label}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-3 text-sm text-ink/70">
                  {solution.validation_passed ? "Independent validator confirmed this placement." : "Validator rejected this placement."}
                </p>
              </div>
            </div>
          ) : (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
              {result.conflicts.map((conflict) => (
                <li key={conflict}>{conflict}</li>
              ))}
            </ul>
          )}
          <div className="mt-4">
            <Button
              variant="ghost"
              onClick={() => {
                setResult(null);
                setMessage("Board ready to edit. Solve again when the grid looks right.");
              }}
            >
              Edit and solve again
            </Button>
          </div>
        </section>
      ) : null}
    </div>
  );
}

import type { Cell, Placement } from "../types";

type Props = {
  rows: number;
  cols: number;
  cells: Cell[];
  selected?: { row: number; col: number } | null;
  placements?: Placement[];
  onSelect?: (cell: Cell) => void;
};

export function PuzzleGrid({ rows, cols, cells, selected, placements = [], onSelect }: Props) {
  const placed = new Set(placements.map((item) => `${item.row}:${item.col}`));
  return (
    <div className="overflow-x-auto">
      <div
        className="inline-grid gap-1 rounded-3xl bg-ink/90 p-3"
        style={{ gridTemplateColumns: `28px repeat(${cols}, minmax(36px, 52px))` }}
      >
        <span />
        {Array.from({ length: cols }, (_, col) => (
          <span key={`c${col}`} className="text-center text-[11px] font-semibold text-cream/70">
            {col + 1}
          </span>
        ))}
        {Array.from({ length: rows }, (_, row) => (
          <Row
            key={row}
            row={row}
            cols={cols}
            cells={cells}
            selected={selected}
            placed={placed}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}

function Row({
  row,
  cols,
  cells,
  selected,
  placed,
  onSelect,
}: {
  row: number;
  cols: number;
  cells: Cell[];
  selected?: { row: number; col: number } | null;
  placed: Set<string>;
  onSelect?: (cell: Cell) => void;
}) {
  return (
    <>
      <span className="flex items-center justify-center text-[11px] font-semibold text-cream/70">{row + 1}</span>
      {Array.from({ length: cols }, (_, col) => {
        const cell = cells.find((item) => item.row === row && item.col === col);
        const key = `${row}:${col}`;
        const isSelected = selected?.row === row && selected?.col === col;
        return (
          <button
            key={key}
            type="button"
            aria-label={`Row ${row + 1} column ${col + 1}${cell?.color_label ? `, ${cell.color_label}` : ""}`}
            onClick={() => cell && onSelect?.(cell)}
            className={`relative aspect-square rounded-xl border text-ink ${isSelected ? "border-white ring-2 ring-amber" : "border-black/10"}`}
            style={{ background: cell?.color_hex || "#d9d0c5" }}
          >
            {cell?.blocked ? <span className="text-lg font-black leading-none text-ink">×</span> : null}
            {cell?.has_cat || placed.has(key) ? <CatMark /> : null}
            {cell && cell.confidence < 0.5 ? (
              <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-terra" />
            ) : null}
          </button>
        );
      })}
    </>
  );
}

function CatMark() {
  return (
    <svg viewBox="0 0 64 64" className="mx-auto h-7 w-7 drop-shadow" aria-hidden="true">
      <circle cx="32" cy="38" r="14" fill="#1c1612" />
      <path d="M18 30 L23 16 L30 30" fill="#1c1612" />
      <path d="M34 30 L41 16 L46 30" fill="#1c1612" />
      <circle cx="27" cy="37" r="2" fill="#fffdf8" />
      <circle cx="37" cy="37" r="2" fill="#fffdf8" />
    </svg>
  );
}

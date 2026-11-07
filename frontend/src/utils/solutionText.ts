import type { Solution } from "../types";

export function solutionInstructions(solution: Solution, total: number): string {
  const lines = [
    `Cat puzzle solution ${solution.index + 1} of ${total}`,
    "Place one cat on each of these cells. Rows and columns are numbered from 1.",
    "",
  ];
  for (const place of solution.placements) {
    lines.push(
      `${place.cat}. Row ${place.row + 1}, column ${place.col + 1} — ${place.color_label ?? "unknown color"}`,
    );
  }
  lines.push("", "Keep the cats from touching, including diagonally.");
  return lines.join("\n");
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { PuzzleSummary } from "../types";

export function HistoryPage() {
  const queryClient = useQueryClient();
  const puzzles = useQuery({
    queryKey: ["puzzles"],
    queryFn: async () => (await api.get<{ items: PuzzleSummary[]; total: number }>("/puzzles")).data,
  });
  const remove = useMutation({
    mutationFn: async (id: string) => api.delete(`/puzzles/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["puzzles"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <h1 className="font-display text-4xl">Puzzle history</h1>
        <Link to="/upload" className="text-sm font-semibold text-amber-dark">
          Upload new
        </Link>
      </div>
      {puzzles.isLoading ? <p>Loading your puzzles…</p> : null}
      {puzzles.data && puzzles.data.items.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-line bg-paper p-8 text-center">
          <p className="font-display text-2xl">Nothing saved yet</p>
          <p className="mt-2 text-sm text-ink/70">Solved and unsolved boards you upload will appear here.</p>
        </div>
      ) : null}
      <div className="overflow-x-auto rounded-3xl border border-line bg-paper">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="text-ink/50">
            <tr>
              <th className="px-4 py-3 font-medium">Screenshot</th>
              <th className="px-4 py-3 font-medium">Board</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Solutions</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {puzzles.data?.items.map((puzzle) => (
              <tr key={puzzle.id} className="border-t border-line">
                <td className="px-4 py-3">{puzzle.original_filename}</td>
                <td className="px-4 py-3">{puzzle.rows && puzzle.cols ? `${puzzle.rows}×${puzzle.cols}` : "—"}</td>
                <td className="px-4 py-3 capitalize">{puzzle.status.replaceAll("_", " ")}</td>
                <td className="px-4 py-3">{puzzle.solution_count}</td>
                <td className="px-4 py-3 text-right">
                  <Link to={`/puzzles/${puzzle.id}`} className="font-semibold text-amber-dark">
                    Open
                  </Link>
                  <button
                    className="ml-3 text-terra"
                    onClick={() => {
                      if (window.confirm("Delete this puzzle and its saved solutions?")) remove.mutate(puzzle.id);
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

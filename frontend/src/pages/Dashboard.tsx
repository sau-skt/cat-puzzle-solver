import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import type { Stats } from "../types";

export function Dashboard() {
  const { user } = useAuth();
  const stats = useQuery({
    queryKey: ["stats"],
    queryFn: async () => (await api.get<Stats>("/puzzles/stats")).data,
  });

  const data = stats.data;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-ink/60">Puzzle desk</p>
          <h1 className="font-display text-4xl">Hello, {user?.full_name.split(" ")[0]}</h1>
        </div>
        <Link to="/upload" className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-cream">
          Upload new puzzle
        </Link>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Puzzles" value={data?.total ?? "–"} />
        <Stat label="Solved" value={data?.solved ?? "–"} />
        <Stat label="No solution" value={data?.no_solution ?? "–"} />
        <Stat label="Success" value={data ? `${Math.round(data.success_rate * 100)}%` : "–"} />
      </div>
      <section className="rounded-3xl border border-line bg-paper p-5 shadow-card">
        <h2 className="font-display text-2xl">Recent activity</h2>
        {stats.isLoading ? <p className="mt-3 text-sm text-ink/60">Loading…</p> : null}
        {data && data.recent.length === 0 ? (
          <p className="mt-3 text-sm text-ink/70">No puzzles yet. Upload a screenshot to start a history.</p>
        ) : null}
        <ul className="mt-3 divide-y divide-line">
          {data?.recent.map((puzzle) => (
            <li key={puzzle.id} className="flex items-center justify-between gap-3 py-3 text-sm">
              <div>
                <p className="font-semibold">{puzzle.original_filename}</p>
                <p className="text-ink/60">
                  {puzzle.rows && puzzle.cols ? `${puzzle.rows}×${puzzle.cols}` : "Board not read"} · {puzzle.status}
                </p>
              </div>
              <Link to={`/puzzles/${puzzle.id}`} className="font-semibold text-amber-dark">
                Open
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <article className="rounded-3xl border border-line bg-paper p-4 shadow-card">
      <p className="text-xs uppercase tracking-wide text-ink/50">{label}</p>
      <p className="mt-2 font-display text-3xl">{value}</p>
    </article>
  );
}

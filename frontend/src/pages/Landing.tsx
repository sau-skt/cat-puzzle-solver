import { ArrowRight, Grid3x3, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

export function Landing() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <header className="flex items-center justify-between">
        <p className="font-display text-2xl">Cat Puzzle Solver</p>
        <div className="flex gap-2">
          <Link to="/login" className="rounded-full px-4 py-2 text-sm font-semibold">
            Log in
          </Link>
          <Link to="/signup" className="rounded-full bg-ink px-4 py-2 text-sm font-semibold text-cream">
            Create account
          </Link>
        </div>
      </header>
      <section className="grid items-center gap-10 py-16 md:grid-cols-[1.2fr_0.8fr]">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-dark">Local vision. Exact logic.</p>
          <h1 className="mt-3 font-display text-5xl leading-tight md:text-6xl">
            Read the board. Place every cat.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-ink/75">
            Upload a screenshot of a colored cat puzzle. The app finds the grid on your machine, lets you correct
            anything it misread, and solves the placement with a constraint engine. No paid AI API.
          </p>
          <Link to="/signup" className="mt-8 inline-flex items-center gap-2 rounded-full bg-amber px-5 py-3 font-semibold text-ink">
            Start solving <ArrowRight size={18} />
          </Link>
        </div>
        <div className="rounded-[28px] bg-ink p-6 text-cream shadow-card">
          <div className="grid grid-cols-5 gap-2">
            {["#d24a4a", "#e0892d", "#e6c84a", "#3e7a5a", "#3c6fbf", "#8a4fbf", "#e07aa8", "#8a5a3c", "#7dba6a", "#d24a4a"].map(
              (color, index) => (
                <div key={index} className="aspect-square rounded-xl" style={{ background: color }}>
                  {index === 2 || index === 7 ? <span className="grid h-full place-items-center text-xl text-ink">×</span> : null}
                </div>
              ),
            )}
          </div>
          <p className="mt-4 text-sm text-cream/70">One cat per row, column, and color. No two cats touch.</p>
        </div>
      </section>
      <section className="grid gap-4 md:grid-cols-3">
        {[
          { icon: Grid3x3, title: "Sees the grid", copy: "OpenCV finds cells, colors, X marks, and cats at any square size." },
          { icon: Sparkles, title: "You stay in control", copy: "Low confidence never becomes a silent guess. Correct the board first." },
          { icon: ShieldCheck, title: "Checked twice", copy: "A separate validator confirms every solution before it is shown." },
        ].map((item) => (
          <article key={item.title} className="rounded-3xl border border-line bg-paper p-5 shadow-card">
            <item.icon className="text-amber-dark" />
            <h2 className="mt-3 font-display text-2xl">{item.title}</h2>
            <p className="mt-2 text-sm text-ink/70">{item.copy}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

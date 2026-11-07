import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-ink text-cream hover:bg-amber-dark disabled:opacity-50",
    ghost: "bg-white text-ink border border-line hover:border-ink disabled:opacity-50",
    danger: "bg-terra text-white hover:opacity-90 disabled:opacity-50",
  }[variant];
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${styles} ${className}`}
      {...props}
    />
  );
}

export function Field({
  label,
  error,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-ink/80">{label}</span>
      <input
        className="w-full rounded-2xl border border-line bg-white px-3 py-2.5 outline-none ring-amber/40 focus:ring-2"
        {...props}
      />
      {error ? <span className="mt-1 block text-terra">{error}</span> : null}
    </label>
  );
}

export function Alert({ kind = "error", children }: { kind?: "error" | "ok" | "warn"; children: ReactNode }) {
  const styles = {
    error: "border-terra/30 bg-terra/10 text-terra",
    ok: "border-sage/30 bg-sage/10 text-sage",
    warn: "border-amber/40 bg-amber/10 text-amber-dark",
  }[kind];
  return <div className={`rounded-2xl border px-3 py-2 text-sm ${styles}`}>{children}</div>;
}

export function Spinner() {
  return <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" />;
}

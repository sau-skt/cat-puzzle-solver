import { useEffect, useId, useMemo, useRef, useState } from "react";
import { api } from "../services/api";

export type Country = {
  iso: string;
  name: string;
  dial: string;
  min: number;
  max: number;
};

const FALLBACK: Country[] = [
  { iso: "AU", name: "Australia", dial: "+61", min: 9, max: 9 },
  { iso: "BD", name: "Bangladesh", dial: "+880", min: 10, max: 10 },
  { iso: "BR", name: "Brazil", dial: "+55", min: 10, max: 11 },
  { iso: "CA", name: "Canada", dial: "+1", min: 10, max: 10 },
  { iso: "CN", name: "China", dial: "+86", min: 11, max: 11 },
  { iso: "FR", name: "France", dial: "+33", min: 9, max: 9 },
  { iso: "DE", name: "Germany", dial: "+49", min: 10, max: 11 },
  { iso: "IN", name: "India", dial: "+91", min: 10, max: 10 },
  { iso: "ID", name: "Indonesia", dial: "+62", min: 9, max: 12 },
  { iso: "JP", name: "Japan", dial: "+81", min: 10, max: 10 },
  { iso: "MX", name: "Mexico", dial: "+52", min: 10, max: 10 },
  { iso: "NP", name: "Nepal", dial: "+977", min: 10, max: 10 },
  { iso: "NG", name: "Nigeria", dial: "+234", min: 10, max: 10 },
  { iso: "PK", name: "Pakistan", dial: "+92", min: 10, max: 10 },
  { iso: "SG", name: "Singapore", dial: "+65", min: 8, max: 8 },
  { iso: "ZA", name: "South Africa", dial: "+27", min: 9, max: 9 },
  { iso: "LK", name: "Sri Lanka", dial: "+94", min: 9, max: 9 },
  { iso: "AE", name: "United Arab Emirates", dial: "+971", min: 9, max: 9 },
  { iso: "GB", name: "United Kingdom", dial: "+44", min: 10, max: 10 },
  { iso: "US", name: "United States", dial: "+1", min: 10, max: 10 },
];

export const DEFAULT_COUNTRY = FALLBACK.find((country) => country.iso === "IN") as Country;

function flag(iso: string): string {
  return iso.toUpperCase().replace(/./g, (char) => String.fromCodePoint(127397 + char.charCodeAt(0)));
}

export function CountryPhoneField({
  country,
  phone,
  onCountry,
  onPhone,
}: {
  country: Country;
  phone: string;
  onCountry: (country: Country) => void;
  onPhone: (phone: string) => void;
}) {
  const [countries, setCountries] = useState<Country[]>(FALLBACK);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const panel = useRef<HTMLDivElement>(null);
  const listId = useId();
  const selected = countries.find((item) => item.iso === country.iso) ?? country;

  useEffect(() => {
    let cancelled = false;
    api
      .get<Country[]>("/auth/countries")
      .then((response) => {
        if (!cancelled && response.data.length) setCountries(response.data);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    function onPointer(event: MouseEvent) {
      if (!panel.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase().replace(/^\+/, "");
    if (!needle) return countries;
    return countries.filter((item) => {
      const dial = item.dial.replace("+", "");
      return item.name.toLowerCase().includes(needle) || item.iso.toLowerCase().includes(needle) || dial.includes(needle);
    });
  }, [countries, query]);

  const hint = selected.min === selected.max ? `${selected.min} digits` : `${selected.min}–${selected.max} digits`;

  return (
    <div className="space-y-3" ref={panel}>
      <div className="block text-sm">
        <span className="mb-1 block font-medium text-ink/80">Country</span>
        <button
          type="button"
          className="flex w-full items-center justify-between rounded-2xl border border-line bg-white px-3 py-2.5 text-left"
          aria-expanded={open}
          aria-controls={listId}
          onClick={() => setOpen((value) => !value)}
        >
          <span>
            {flag(selected.iso)} {selected.name}
          </span>
          <span className="font-semibold text-ink/70">{selected.dial}</span>
        </button>
        {open ? (
          <div className="mt-2 rounded-2xl border border-line bg-white p-2 shadow-card">
            <input
              aria-label="Search country"
              className="w-full rounded-xl border border-line px-3 py-2 outline-none ring-amber/40 focus:ring-2"
              placeholder="Search by name or code"
              value={query}
              autoFocus
              onChange={(event) => setQuery(event.target.value)}
            />
            <ul id={listId} role="listbox" className="mt-2 max-h-48 overflow-auto">
              {matches.length ? (
                matches.map((item) => (
                  <li key={item.iso}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={item.iso === selected.iso}
                      className="flex w-full items-center justify-between rounded-xl px-2 py-1.5 text-left hover:bg-cream"
                      onClick={() => {
                        onCountry(item);
                        setOpen(false);
                        setQuery("");
                      }}
                    >
                      <span>
                        {flag(item.iso)} {item.name}
                      </span>
                      <span className="text-ink/60">{item.dial}</span>
                    </button>
                  </li>
                ))
              ) : (
                <li className="px-2 py-2 text-ink/60">No country matches that search.</li>
              )}
            </ul>
          </div>
        ) : null}
      </div>
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-ink/80">Phone number</span>
        <span className="flex overflow-hidden rounded-2xl border border-line bg-white ring-amber/40 focus-within:ring-2">
          <span className="grid place-items-center border-r border-line px-3 font-semibold text-ink/70">{selected.dial}</span>
          <input
            className="w-full px-3 py-2.5 outline-none"
            inputMode="numeric"
            autoComplete="tel-national"
            aria-label="Phone number"
            placeholder={hint}
            value={phone}
            required
            onChange={(event) => onPhone(event.target.value.replace(/[^\d]/g, "").slice(0, selected.max))}
          />
        </span>
        <span className="mt-1 block text-ink/55">National number, {hint}. The country code is stored with it.</span>
      </label>
    </div>
  );
}

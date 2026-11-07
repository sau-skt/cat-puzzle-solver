import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CountryPhoneField, DEFAULT_COUNTRY, type Country } from "../components/CountryPhoneField";
import { Alert, Button, Field } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import type { User } from "../types";
import { passwordProblems } from "../utils/password";

export function Signup() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", confirm_password: "" });
  const [country, setCountry] = useState<Country>(DEFAULT_COUNTRY);
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const problems = form.password ? passwordProblems(form.password) : [];

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (problems.length) {
      setError(problems[0]);
      return;
    }
    if (form.password !== form.confirm_password) {
      setError("Passwords do not match.");
      return;
    }
    if (phone.length < country.min || phone.length > country.max) {
      setError(
        country.min === country.max
          ? `Enter a ${country.min}-digit phone number for ${country.name}.`
          : `Enter a ${country.min}–${country.max} digit phone number for ${country.name}.`,
      );
      return;
    }
    setPending(true);
    try {
      const response = await api.post<User>("/auth/signup", {
        ...form,
        country_iso: country.iso,
        dial_code: country.dial,
        phone_number: phone,
      });
      setUser(response.data);
      navigate("/dashboard");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthCard title="Create your account" subtitle="Your puzzles stay on this account.">
      <form className="space-y-4" onSubmit={onSubmit}>
        {error ? <Alert>{error}</Alert> : null}
        <Field label="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
        <Field label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        <CountryPhoneField country={country} phone={phone} onCountry={setCountry} onPhone={setPhone} />
        <Field label="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
        {problems.length ? <p className="text-sm text-ink/60">{problems.join(" ")}</p> : null}
        <Field
          label="Confirm password"
          type="password"
          value={form.confirm_password}
          onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
          required
        />
        <Button className="w-full" disabled={pending}>
          {pending ? "Creating account…" : "Sign up"}
        </Button>
      </form>
      <p className="mt-4 text-sm text-ink/70">
        Already registered? <Link to="/login" className="font-semibold text-amber-dark">Log in</Link>
      </p>
    </AuthCard>
  );
}

export function AuthCard({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="mx-auto grid min-h-screen max-w-md place-items-center px-4 py-10">
      <div className="w-full rounded-[28px] border border-line bg-paper p-6 shadow-card">
        <p className="font-display text-3xl">{title}</p>
        <p className="mb-5 mt-1 text-sm text-ink/65">{subtitle}</p>
        {children}
      </div>
    </div>
  );
}

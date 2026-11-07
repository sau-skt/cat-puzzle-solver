import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Alert, Button, Field } from "../components/ui";
import { AuthCard } from "./Signup";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import type { User } from "../types";

export function Login() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const response = await api.post<User>("/auth/login", { email, password, remember_me: remember });
      setUser(response.data);
      navigate("/dashboard");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthCard title="Welcome back" subtitle="Log in to open your puzzle desk.">
      <form className="space-y-4" onSubmit={onSubmit}>
        {error ? <Alert>{error}</Alert> : null}
        <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Field label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          Remember me
        </label>
        <Button className="w-full" disabled={pending}>
          {pending ? "Signing in…" : "Log in"}
        </Button>
      </form>
      <div className="mt-4 flex justify-between text-sm">
        <Link to="/forgot-password" className="font-semibold text-amber-dark">Forgot password</Link>
        <Link to="/signup" className="font-semibold">Create account</Link>
      </div>
    </AuthCard>
  );
}

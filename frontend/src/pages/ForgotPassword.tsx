import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Field } from "../components/ui";
import { AuthCard } from "./Signup";
import { api, errorMessage } from "../services/api";
import { passwordProblems } from "../utils/password";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const response = await api.post<{ message: string; reset_token?: string | null }>("/auth/forgot-password", { email });
      setMessage(response.data.message);
      setToken(response.data.reset_token ?? null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <AuthCard title="Forgot password" subtitle="We will send a reset link if the account exists.">
      <form className="space-y-4" onSubmit={onSubmit}>
        {error ? <Alert>{error}</Alert> : null}
        {message ? <Alert kind="ok">{message}</Alert> : null}
        <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Button className="w-full">Send reset link</Button>
      </form>
      {token ? (
        <p className="mt-4 text-sm">
          Mail is not configured on this machine.{" "}
          <Link className="font-semibold text-amber-dark" to={`/reset-password?token=${encodeURIComponent(token)}`}>
            Open the reset page
          </Link>
        </p>
      ) : null}
      <p className="mt-4 text-sm">
        <Link to="/login">Back to login</Link>
      </p>
    </AuthCard>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const problems = passwordProblems(password);
    if (problems.length) {
      setError(problems[0]);
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    try {
      const response = await api.post<{ message: string }>("/auth/reset-password", {
        token: params.get("token") || "",
        password,
        confirm_password: confirm,
      });
      setDone(response.data.message);
      setTimeout(() => navigate("/login"), 800);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <AuthCard title="Choose a new password" subtitle="Reset links expire after 30 minutes.">
      <form className="space-y-4" onSubmit={onSubmit}>
        {error ? <Alert>{error}</Alert> : null}
        {done ? <Alert kind="ok">{done}</Alert> : null}
        <Field label="New password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <Field label="Confirm password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
        <Button className="w-full">Update password</Button>
      </form>
    </AuthCard>
  );
}

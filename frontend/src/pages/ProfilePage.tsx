import { FormEvent, useState } from "react";
import { Alert, Button, Field } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import { passwordProblems } from "../utils/password";

export function ProfilePage() {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user?.full_name ?? "");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  async function saveName(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      const response = await api.patch("/auth/me", { full_name: name });
      setUser(response.data);
      setNotice("Profile updated.");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
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
      await api.post("/auth/change-password", {
        current_password: current,
        password,
        confirm_password: confirm,
      });
      setCurrent("");
      setPassword("");
      setConfirm("");
      setNotice("Password updated.");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="font-display text-4xl">Account</h1>
      {error ? <Alert>{error}</Alert> : null}
      {notice ? <Alert kind="ok">{notice}</Alert> : null}
      <section className="rounded-3xl border border-line bg-paper p-5">
        <p className="text-sm text-ink/60">{user?.email}</p>
        <p className="mt-1 text-sm">{user?.phone_e164 ? `Phone ${user.phone_e164}` : "No phone number on this account"}</p>
        <p className="mt-1 text-sm">{user?.is_verified ? "Email verified" : "Email not verified"}</p>
        <form className="mt-4 space-y-3" onSubmit={saveName}>
          <Field label="Full name" value={name} onChange={(e) => setName(e.target.value)} />
          <Button>Save profile</Button>
        </form>
      </section>
      <section className="rounded-3xl border border-line bg-paper p-5">
        <h2 className="font-display text-2xl">Password</h2>
        <form className="mt-4 space-y-3" onSubmit={savePassword}>
          <Field label="Current password" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
          <Field label="New password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Field label="Confirm password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <Button>Change password</Button>
        </form>
      </section>
    </div>
  );
}

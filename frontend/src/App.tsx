import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppShell } from "./layouts/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { ForgotPassword, ResetPassword } from "./pages/ForgotPassword";
import { HistoryPage } from "./pages/HistoryPage";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { ProfilePage } from "./pages/ProfilePage";
import { PuzzleWorkspace } from "./pages/PuzzleWorkspace";
import { Signup } from "./pages/Signup";
import { UploadPage } from "./pages/UploadPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/puzzles/:id" element={<PuzzleWorkspace />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

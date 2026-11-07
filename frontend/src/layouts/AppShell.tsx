import { History, LayoutDashboard, LogOut, PawPrint, Upload, UserRound } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const links = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/history", label: "History", icon: History },
  { to: "/profile", label: "Profile", icon: UserRound },
];

export function AppShell() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <aside className="border-b border-white/10 bg-ink text-cream md:min-h-screen md:border-b-0">
        <div className="flex items-center gap-2 px-5 py-5">
          <PawPrint className="text-amber" />
          <span className="font-display text-xl">Cat Puzzle</span>
        </div>
        <nav className="flex gap-2 overflow-x-auto px-3 pb-3 md:block md:space-y-1 md:px-3">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `flex items-center gap-2 whitespace-nowrap rounded-2xl px-3 py-2 text-sm ${isActive ? "bg-white/10 text-white" : "text-cream/70 hover:bg-white/5"}`
              }
            >
              <link.icon size={16} />
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden px-4 py-4 md:block">
          <p className="truncate text-sm text-cream/80">{user?.full_name}</p>
          <button className="mt-3 flex items-center gap-2 text-sm text-cream/70 hover:text-white" onClick={() => logout()}>
            <LogOut size={16} /> Log out
          </button>
        </div>
      </aside>
      <div>
        <div className="flex items-center justify-between border-b border-line px-4 py-3 md:hidden">
          <p className="truncate text-sm">{user?.full_name}</p>
          <button className="text-sm font-semibold" onClick={() => logout()}>
            Log out
          </button>
        </div>
        <main className="mx-auto max-w-6xl px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

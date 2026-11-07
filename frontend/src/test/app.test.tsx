import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, vi } from "vitest";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AuthProvider } from "../context/AuthContext";
import { Landing } from "../pages/Landing";
import { Signup } from "../pages/Signup";
import { passwordProblems } from "../utils/password";
import { solutionInstructions } from "../utils/solutionText";

const get = vi.fn();
const post = vi.fn();

vi.mock("../services/api", () => ({
  api: {
    get: (...args: unknown[]) => get(...args),
    post: (...args: unknown[]) => post(...args),
    interceptors: { response: { use: vi.fn() } },
  },
  errorMessage: () => "Request failed",
}));

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  get.mockRejectedValue(new Error("offline"));
});

describe("password rules", () => {
  it("rejects a weak password and accepts a strong one", () => {
    expect(passwordProblems("password").length).toBeGreaterThan(0);
    expect(passwordProblems("ValidPass1!")).toEqual([]);
  });
});

describe("solution instructions", () => {
  it("uses one-based coordinates from the solver payload", () => {
    const text = solutionInstructions(
      {
        id: "s",
        index: 0,
        validation_passed: true,
        execution_time_ms: 2,
        placements: [{ cat: 1, row: 0, col: 3, color_id: 2, color_label: "pink", color_hex: "#ff8ad4" }],
      },
      1,
    );
    expect(text).toContain("Row 1, column 4 — pink");
  });
});

describe("landing", () => {
  it("links visitors to signup", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Landing />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("link", { name: /start solving/i })).toHaveAttribute("href", "/signup");
  });
});

describe("signup form", () => {
  it("shows a password error before calling the API", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AuthProvider>
          <Signup />
        </AuthProvider>
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText(/full name/i), "Saurabh Singh");
    await user.type(screen.getByLabelText(/email/i), "saurabh@example.com");
    await user.type(screen.getByLabelText(/^phone number$/i), "9876543210");
    await user.type(screen.getByLabelText(/^password$/i), "password");
    await user.type(screen.getByLabelText(/confirm password/i), "password");
    await user.click(screen.getByRole("button", { name: /sign up/i }));
    expect(screen.getByText("Add an uppercase letter.")).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
  });

  it("filters countries by name and calling code", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <AuthProvider>
          <Signup />
        </AuthProvider>
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: /india/i }));
    const search = screen.getByLabelText(/search country/i);
    await user.type(search, "cana");
    expect(screen.getByRole("option", { name: /canada/i })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /india/i })).not.toBeInTheDocument();
    await user.clear(search);
    await user.type(search, "+44");
    await user.click(screen.getByRole("option", { name: /united kingdom/i }));
    expect(screen.getByRole("button", { name: /united kingdom/i })).toHaveTextContent("+44");
  });
});

describe("protected routes", () => {
  it("sends anonymous visitors to login", async () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AuthProvider>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<h1>Secret desk</h1>} />
            </Route>
            <Route path="/login" element={<h1>Login screen</h1>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: /login screen/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /secret desk/i })).not.toBeInTheDocument();
  });
});

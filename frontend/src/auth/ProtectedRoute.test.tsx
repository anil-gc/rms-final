import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { AuthContext } from "./auth-context";
import type { AuthValue } from "./auth-context";
import { ProtectedRoute } from "./ProtectedRoute";
import type { User } from "../types";

const staff: User = {
  id: 1,
  username: "test.staff",
  first_name: "",
  last_name: "",
  role: "waiter",
  is_active: true,
  must_change_pin: false,
};
const owner: User = { ...staff, role: "owner" };
function route(
  user: User | null,
  status: AuthValue["status"] = user ? "authenticated" : "anonymous",
) {
  const auth: AuthValue = {
    user,
    status,
    loginPath:
      user?.role === "owner" || !user ? "/login/owner" : "/login/staff",
    refresh: vi.fn(),
    loginOwner: vi.fn(),
    loginStaff: vi.fn(),
    logout: vi.fn(),
    updateUser: vi.fn(),
  };
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={["/staff"]}>
        <Routes>
          <Route
            path="/login/owner"
            element={<div>Owner sign in screen</div>}
          />
          <Route
            path="/change-pin"
            element={<div>Required PIN change screen</div>}
          />
          <Route element={<ProtectedRoute />}>
            <Route element={<ProtectedRoute ownerOnly />}>
              <Route path="/staff" element={<div>Staff directory</div>} />
            </Route>
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}
describe("account route boundaries", () => {
  it("redirects an anonymous visitor to sign in", () => {
    route(null);
    expect(screen.getByText("Owner sign in screen")).toBeInTheDocument();
  });
  it("sends a temporary-PIN session to its required flow before checking the Owner page", () => {
    route({ ...staff, must_change_pin: true });
    expect(screen.getByText("Required PIN change screen")).toBeInTheDocument();
  });
  it("does not expose staff management to staff roles", () => {
    route(staff);
    expect(
      screen.getByRole("heading", { name: "Owner access required" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Staff directory")).not.toBeInTheDocument();
  });
  it("allows an Owner with a ready session", () => {
    route(owner);
    expect(screen.getByText("Staff directory")).toBeInTheDocument();
  });
  it("holds the route while the server checks the session", () => {
    route(null, "loading");
    expect(screen.getByText("Opening your workspace…")).toBeInTheDocument();
    expect(screen.queryByText("Staff directory")).not.toBeInTheDocument();
  });
  it("shows reconnect state instead of treating a network failure as logout", () => {
    route(owner, "unavailable");
    expect(
      screen.getByRole("heading", { name: "Let’s reconnect." }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Owner sign in screen")).not.toBeInTheDocument();
  });
});

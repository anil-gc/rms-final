import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { RestaurantPage } from "./RestaurantPage";
import { MenuPage } from "./MenuPage";
import { TablesPage } from "./TablesPage";
import { AuthContext } from "../auth/auth-context";
import type { AuthValue } from "../auth/auth-context";
import { workspace } from "../lib/workspace";
import { ApiError } from "../lib/api";

vi.mock("../lib/workspace", async (original) => ({
  ...(await original<typeof import("../lib/workspace")>()),
  workspace: {
    restaurant: vi.fn(),
    categories: vi.fn(),
    items: vi.fn(),
    tables: vi.fn(),
    saveRestaurant: vi.fn(),
  },
}));

const profile = {
  id: 1,
  name: "Test restaurant",
  description: "",
  address: "Kathmandu",
  contact_phone: "",
  email: "",
  currency: "NPR" as const,
  opening_time: null,
  closing_time: null,
  logo_url: null,
  is_active: true,
  updated_at: "test-version",
};
function context(role: "owner" | "manager" | "waiter" = "owner"): AuthValue {
  return {
    user: {
      id: 1,
      username: "synthetic-user",
      first_name: "",
      last_name: "",
      role,
      is_active: true,
      must_change_pin: false,
    },
    status: "authenticated",
    loginPath: "/login/owner",
    refresh: vi.fn(),
    loginOwner: vi.fn(),
    loginStaff: vi.fn(),
    logout: vi.fn(),
    updateUser: vi.fn(),
  };
}

describe("Phase 3 screen boundaries", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(workspace.restaurant).mockResolvedValue(profile);
    vi.mocked(workspace.categories).mockResolvedValue([]);
    vi.mocked(workspace.items).mockResolvedValue([]);
    vi.mocked(workspace.tables).mockResolvedValue([]);
  });

  it("does not treat a server failure as an empty restaurant setup", async () => {
    vi.mocked(workspace.restaurant).mockRejectedValue(
      new ApiError("Connection unavailable", 0),
    );
    render(
      <AuthContext.Provider value={context()}>
        <MemoryRouter>
          <RestaurantPage />
        </MemoryRouter>
      </AuthContext.Provider>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Connection unavailable",
    );
    expect(
      screen.queryByRole("button", { name: "Create restaurant profile" }),
    ).not.toBeInTheDocument();
  });

  it("lets Manager set up the singleton using the existing API contract", async () => {
    vi.mocked(workspace.restaurant).mockResolvedValue(null);
    vi.mocked(workspace.saveRestaurant).mockResolvedValue(profile);
    render(
      <AuthContext.Provider value={context("manager")}>
        <MemoryRouter>
          <RestaurantPage />
        </MemoryRouter>
      </AuthContext.Provider>,
    );
    fireEvent.change(await screen.findByLabelText("Restaurant name"), {
      target: { value: "Test restaurant" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Create restaurant profile" }),
    );
    await waitFor(() =>
      expect(workspace.saveRestaurant).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Test restaurant", currency: "NPR" }),
        false,
      ),
    );
  });

  it("shows actual menu data to staff without mutation controls", async () => {
    vi.mocked(workspace.categories).mockResolvedValue([
      {
        id: 2,
        name: "Momo",
        description: "",
        sort_order: 0,
        is_active: true,
        updated_at: "test",
      },
    ]);
    vi.mocked(workspace.items).mockResolvedValue([
      {
        id: 3,
        name: "Vegetable momo",
        category: 2,
        category_name: "Momo",
        price: "200.50",
        description: "Freshly steamed",
        is_available: false,
        effective_available: false,
        is_active: true,
        updated_at: "test",
      },
    ]);
    render(
      <AuthContext.Provider value={context("waiter")}>
        <MemoryRouter>
          <MenuPage />
        </MemoryRouter>
      </AuthContext.Provider>,
    );
    expect(
      await screen.findByRole("heading", { name: "Vegetable momo" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Add item" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Edit item Vegetable momo" }),
    ).not.toBeInTheDocument();
  });

  it("keeps table creation disabled until a profile exists", async () => {
    vi.mocked(workspace.restaurant).mockResolvedValue(null);
    render(
      <AuthContext.Provider value={context()}>
        <MemoryRouter>
          <TablesPage />
        </MemoryRouter>
      </AuthContext.Provider>,
    );
    expect(
      await screen.findByText(/Set up your restaurant profile before/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add table" })).toBeDisabled();
  });
});

import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { AuthContext } from "../../auth/auth-context";
import type { AuthValue } from "../../auth/auth-context";
import type { Role } from "../../types";
import { ProtectedRoute } from "../../auth/ProtectedRoute";
import { AppLayout } from "../../components/AppLayout";
import { ApiError } from "../../lib/api";
import { workspace } from "../../lib/workspace";
import { orderApi } from "./api";
import type { Batch, OrderDetail } from "./api";
import { WaiterOrdersPage } from "./WaiterOrdersPage";
import { CashierOrdersPage } from "./CashierOrdersPage";
import { OrdersAccess } from "./OrdersAccess";

vi.mock("../../lib/workspace", () => ({
  workspace: {
    tables: vi.fn(),
    items: vi.fn(),
    categories: vi.fn(),
  },
}));
vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  orderApi: {
    active: vi.fn(),
    open: vi.fn(),
    submit: vi.fn(),
    batches: vi.fn(),
    approve: vi.fn(),
    reject: vi.fn(),
  },
}));

const timestamp = "2026-10-25T10:00:00Z";
const table = {
  id: 5,
  name: "T5",
  capacity: 4,
  status: "available" as const,
  is_active: true,
  updated_at: timestamp,
};
const item = {
  id: 3,
  category: 2,
  category_name: "Meals",
  name: "Momo",
  description: "Steamed dumplings",
  price: "200.05",
  is_active: true,
  is_available: true,
  effective_available: true,
  updated_at: timestamp,
};
const batch: Batch = {
  id: "batch-1",
  order: "order-1",
  sequence: 1,
  status: "pending",
  table_name: "T5",
  submitted_by: 1,
  submitted_by_name: "waiter-test",
  submitted_at: timestamp,
  reviewed_by: null,
  reviewed_by_name: null,
  reviewed_at: null,
  rejection_reason: "",
  lines: [
    {
      id: 1,
      menu_item: 3,
      item_name: "Momo",
      unit_price: "200.05",
      quantity: 2,
      line_total: "400.10",
      created_at: timestamp,
    },
  ],
  total: "400.10",
};
const order: OrderDetail = {
  id: "order-1",
  session: "visit-1",
  table: 5,
  table_name: "T5",
  state: "open",
  opened_at: timestamp,
  batches: [],
  totals: { pending: "0.00", approved: "0.00", rejected: "0.00" },
  events: [],
};

function auth(role: Role = "waiter", mustChange = false): AuthValue {
  return {
    user: {
      id: 1,
      username: "test",
      first_name: "",
      last_name: "",
      role,
      is_active: true,
      must_change_pin: mustChange,
    },
    status: "authenticated",
    loginPath: "/login/staff",
    refresh: vi.fn(),
    loginOwner: vi.fn(),
    loginStaff: vi.fn(),
    logout: vi.fn(),
    updateUser: vi.fn(),
  };
}
function mount(component: React.ReactNode, role: Role = "waiter") {
  return render(
    <AuthContext.Provider value={auth(role)}>
      <MemoryRouter>{component}</MemoryRouter>
    </AuthContext.Provider>,
  );
}
async function selectTable() {
  fireEvent.click(
    await screen.findByRole("button", { name: /Select table T5/ }),
  );
  await screen.findByRole("heading", { name: "Add a new batch" });
  await screen.findByRole("button", { name: "Add Momo" });
}

describe("Waiter ordering", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    sessionStorage.clear();
    vi.mocked(workspace.tables).mockResolvedValue([table]);
    vi.mocked(workspace.items).mockResolvedValue([item]);
    vi.mocked(workspace.categories).mockResolvedValue([
      {
        id: 2,
        name: "Meals",
        description: "",
        sort_order: 0,
        is_active: true,
        updated_at: timestamp,
      },
    ]);
    vi.mocked(orderApi.active).mockResolvedValue(order);
    vi.mocked(orderApi.open).mockResolvedValue(order);
    vi.mocked(orderApi.submit).mockResolvedValue(batch);
  });

  it("selects a table and opens a session only on explicit confirmation", async () => {
    vi.mocked(orderApi.active)
      .mockResolvedValueOnce(null)
      .mockResolvedValue(order);
    mount(<WaiterOrdersPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: /Select table T5/ }),
    );
    expect(orderApi.open).not.toHaveBeenCalled();
    fireEvent.click(
      await screen.findByRole("button", { name: "Start dining session" }),
    );
    await screen.findByRole("heading", { name: "Add a new batch" });
    expect(orderApi.open).toHaveBeenCalledWith(5);
  });

  it("browses categories/search and prevents unavailable selections", async () => {
    vi.mocked(workspace.items).mockResolvedValue([
      item,
      { ...item, id: 4, name: "Tea", effective_available: false },
    ]);
    mount(<WaiterOrdersPage />);
    await selectTable();
    expect(screen.getByRole("button", { name: "Unavailable" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Search food"), {
      target: { value: "Tea" },
    });
    expect(
      screen.queryByRole("button", { name: "Add Momo" }),
    ).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Category"), {
      target: { value: "2" },
    });
    expect(screen.getByText("Tea")).toBeInTheDocument();
  });

  it("adds/removes items, validates quantities and calculates exact subtotal", async () => {
    mount(<WaiterOrdersPage />);
    await selectTable();
    fireEvent.click(screen.getByRole("button", { name: "Add Momo" }));
    const quantity = screen.getByLabelText("Quantity for Momo");
    fireEvent.change(quantity, { target: { value: "2" } });
    expect(screen.getAllByText("NPR 400.10").length).toBeGreaterThan(0);
    fireEvent.change(quantity, { target: { value: "1.5" } });
    expect(screen.getByRole("alert")).toHaveTextContent("whole quantities");
    expect(quantity).toHaveValue(2);
    fireEvent.click(screen.getByRole("button", { name: "Remove Momo" }));
    expect(screen.getByText("Your new batch is empty.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Submit for Cashier approval" }),
    ).toBeDisabled();
  });

  it("submits once, clears only the composer and refreshes authoritative batches", async () => {
    let resolve!: (value: Batch) => void;
    vi.mocked(orderApi.submit).mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    mount(<WaiterOrdersPage />);
    await selectTable();
    fireEvent.click(screen.getByRole("button", { name: "Add Momo" }));
    const submit = screen.getByRole("button", {
      name: "Submit for Cashier approval",
    });
    fireEvent.click(submit);
    fireEvent.click(submit);
    expect(orderApi.submit).toHaveBeenCalledTimes(1);
    vi.mocked(orderApi.active).mockResolvedValue({
      ...order,
      batches: [batch],
      totals: { ...order.totals, pending: batch.total },
    });
    resolve(batch);
    await screen.findByText(/Batch 1 submitted/);
    expect(screen.getByText("Your new batch is empty.")).toBeInTheDocument();
    expect(
      screen.getByText("pending", { selector: ".order-status" }),
    ).toBeInTheDocument();
    expect(orderApi.submit).toHaveBeenCalledWith(
      "order-1",
      expect.objectContaining({ lines: [{ menu_item: 3, quantity: 1 }] }),
    );
  });

  it("keeps approved history intact when adding another batch", async () => {
    const approved: Batch = {
      ...batch,
      status: "approved",
      reviewed_by: 2,
      reviewed_by_name: "cashier",
      reviewed_at: timestamp,
    };
    vi.mocked(orderApi.active).mockResolvedValue({
      ...order,
      batches: [approved],
      totals: { ...order.totals, approved: batch.total },
    });
    vi.mocked(orderApi.submit).mockResolvedValue({
      ...batch,
      id: "batch-2",
      sequence: 2,
    });
    mount(<WaiterOrdersPage />);
    await selectTable();
    fireEvent.click(screen.getByRole("button", { name: "Add Momo" }));
    vi.mocked(orderApi.active).mockResolvedValue({
      ...order,
      batches: [approved, { ...batch, id: "batch-2", sequence: 2 }],
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Submit for Cashier approval" }),
    );
    await screen.findByText(/Batch 2 submitted/);
    expect(screen.getByLabelText("Batch 1 for T5")).toHaveTextContent(
      "approved",
    );
    expect(screen.getByLabelText("Batch 2 for T5")).toHaveTextContent(
      "pending",
    );
  });

  it("freezes a lost-response submission and explicitly retries the identical key/payload", async () => {
    vi.mocked(orderApi.submit)
      .mockRejectedValueOnce(new ApiError("Connection lost", 0))
      .mockResolvedValue(batch);
    const view = mount(<WaiterOrdersPage />);
    await selectTable();
    fireEvent.click(screen.getByRole("button", { name: "Add Momo" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Submit for Cashier approval" }),
    );
    await screen.findByText(/submission is unconfirmed/);
    const payload = vi.mocked(orderApi.submit).mock.calls[0][1];
    expect(screen.getByRole("button", { name: "Add Momo" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /Select table T5/ }),
    ).toBeDisabled();
    view.unmount();
    mount(<WaiterOrdersPage />);
    await selectTable();
    await screen.findByText(/submission is unconfirmed/);
    expect(orderApi.submit).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Retry same batch" }));
    await screen.findByText(/Batch 1 submitted/);
    expect(orderApi.submit).toHaveBeenLastCalledWith("order-1", payload);
    expect(sessionStorage.length).toBe(0);
  });

  it("shows definite validation errors and allows correction without unsafe replay", async () => {
    vi.mocked(orderApi.submit).mockRejectedValue(
      new ApiError("Items unavailable", 400),
    );
    mount(<WaiterOrdersPage />);
    await selectTable();
    fireEvent.click(screen.getByRole("button", { name: "Add Momo" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Submit for Cashier approval" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Items unavailable",
    );
    expect(screen.getByRole("button", { name: "Add Momo" })).toBeEnabled();
    expect(orderApi.submit).toHaveBeenCalledTimes(1);
  });

  it("handles table/network failure as an error instead of an empty restaurant", async () => {
    vi.mocked(workspace.tables).mockRejectedValue(
      new ApiError("No connection", 0),
    );
    mount(<WaiterOrdersPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No connection");
    expect(screen.queryByText(/No active tables/)).not.toBeInTheDocument();
  });
});

describe("Cashier approvals", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
      configurable: true,
      value: vi.fn(function (this: HTMLDialogElement) {
        this.open = true;
      }),
    });
    Object.defineProperty(HTMLDialogElement.prototype, "close", {
      configurable: true,
      value: vi.fn(function (this: HTMLDialogElement) {
        this.open = false;
      }),
    });
    vi.mocked(orderApi.batches).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [batch],
    });
    vi.mocked(orderApi.approve).mockResolvedValue({
      ...batch,
      status: "approved",
    });
    vi.mocked(orderApi.reject).mockResolvedValue({
      ...batch,
      status: "rejected",
    });
  });

  it("shows pending amounts and confirms approval before refreshing", async () => {
    mount(<CashierOrdersPage />, "cashier");
    fireEvent.click(
      await screen.findByRole("button", { name: "Approve batch 1" }),
    );
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getAllByText("NPR 400.10")).toHaveLength(2);
    expect(orderApi.approve).not.toHaveBeenCalled();
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Confirm approval" }),
    );
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(orderApi.approve).toHaveBeenCalledWith("batch-1");
    expect(orderApi.batches).toHaveBeenCalledTimes(2);
  });

  it("requires a meaningful rejection reason and sends it with confirmation", async () => {
    mount(<CashierOrdersPage />, "cashier");
    fireEvent.click(
      await screen.findByRole("button", { name: "Reject batch 1" }),
    );
    const confirm = screen.getByRole("button", { name: "Confirm rejection" });
    expect(confirm).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Rejection reason"), {
      target: { value: "  Sold out  " },
    });
    fireEvent.click(confirm);
    await waitFor(() =>
      expect(orderApi.reject).toHaveBeenCalledWith("batch-1", "Sold out"),
    );
  });

  it("refreshes and explains a concurrent-review conflict", async () => {
    vi.mocked(orderApi.approve).mockRejectedValue(
      new ApiError("Already reviewed", 409),
    );
    mount(<CashierOrdersPage />, "cashier");
    fireEvent.click(
      await screen.findByRole("button", { name: "Approve batch 1" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm approval" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Already reviewed",
    );
    expect(
      screen.getByRole("button", { name: "Confirm approval" }),
    ).toBeDisabled();
    expect(orderApi.batches).toHaveBeenCalledTimes(2);
  });

  it("filters history and displays the responsible cashier and time", async () => {
    mount(<CashierOrdersPage />, "cashier");
    await screen.findByText("waiter-test", { exact: false });
    vi.mocked(orderApi.batches).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          ...batch,
          status: "approved",
          reviewed_by_name: "cashier-reviewer",
          reviewed_at: timestamp,
        },
      ],
    });
    fireEvent.change(screen.getByLabelText("Show batches"), {
      target: { value: "approved" },
    });
    expect(
      await screen.findByText(/Approved by cashier-reviewer/),
    ).toBeInTheDocument();
    expect(orderApi.batches).toHaveBeenLastCalledWith("approved", 1);
    expect(
      screen.queryByRole("button", { name: "Approve batch 1" }),
    ).not.toBeInTheDocument();
  });

  it("can return to the previous page when concurrent reviews empty a later page", async () => {
    vi.mocked(orderApi.batches)
      .mockResolvedValueOnce({
        count: 21,
        next: "page-2",
        previous: null,
        results: [batch],
      })
      .mockRejectedValueOnce(new ApiError("That page no longer exists", 404))
      .mockResolvedValue({
        count: 1,
        next: null,
        previous: null,
        results: [batch],
      });
    mount(<CashierOrdersPage />, "cashier");
    fireEvent.click(await screen.findByRole("button", { name: "Next page" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "no longer exists",
    );
    fireEvent.click(screen.getByRole("button", { name: "Previous page" }));
    await screen.findByRole("button", { name: "Approve batch 1" });
    expect(orderApi.batches).toHaveBeenLastCalledWith("pending", 1);
  });
});

describe("Order access and navigation", () => {
  it("clears an unsent composer when a different Waiter identity replaces the session", async () => {
    sessionStorage.clear();
    vi.mocked(workspace.tables).mockResolvedValue([table]);
    vi.mocked(workspace.items).mockResolvedValue([item]);
    vi.mocked(workspace.categories).mockResolvedValue([]);
    vi.mocked(orderApi.active).mockResolvedValue(order);
    function tree(id: number) {
      const value = auth();
      value.user = { ...value.user!, id };
      return (
        <AuthContext.Provider value={value}>
          <MemoryRouter>
            <Routes>
              <Route element={<OrdersAccess role="waiter" />}>
                <Route path="/" element={<WaiterOrdersPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </AuthContext.Provider>
      );
    }
    const view = render(tree(1));
    await selectTable();
    fireEvent.click(screen.getByRole("button", { name: "Add Momo" }));
    expect(screen.getByLabelText("Quantity for Momo")).toHaveValue(1);
    view.rerender(tree(2));
    await selectTable();
    expect(screen.getByText("Your new batch is empty.")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Quantity for Momo"),
    ).not.toBeInTheDocument();
  });
  it.each(["owner", "manager", "waiter", "cashier", "chef"] as Role[])(
    "shows only %s role navigation",
    (role) => {
      mount(<AppLayout />, role);
      expect(
        screen.queryByRole("link", { name: "Waiter orders" }) !== null,
      ).toBe(role === "waiter");
      expect(
        screen.queryByRole("link", { name: "Cashier approvals" }) !== null,
      ).toBe(role === "cashier");
    },
  );

  it("keeps temporary-PIN routing ahead of order role guards", () => {
    render(
      <AuthContext.Provider value={auth("waiter", true)}>
        <MemoryRouter initialEntries={["/orders/waiter"]}>
          <Routes>
            <Route path="/change-pin" element={<div>Change PIN first</div>} />
            <Route element={<ProtectedRoute />}>
              <Route element={<OrdersAccess role="waiter" />}>
                <Route
                  path="/orders/waiter"
                  element={<div>Order composer</div>}
                />
              </Route>
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>,
    );
    expect(screen.getByText("Change PIN first")).toBeInTheDocument();
    expect(screen.queryByText("Order composer")).not.toBeInTheDocument();
  });

  it("denies a direct Cashier route to an Owner", () => {
    mount(
      <Routes>
        <Route element={<OrdersAccess role="cashier" />}>
          <Route path="/" element={<div>Cashier queue</div>} />
        </Route>
      </Routes>,
      "owner",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("cannot access");
    expect(screen.queryByText("Cashier queue")).not.toBeInTheDocument();
  });
});

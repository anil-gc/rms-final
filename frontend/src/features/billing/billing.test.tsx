import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { BillingDashboard } from "./BillingDashboard";
import { PaymentForm } from "./PaymentForm";

const activeBillsMock = vi.fn();
const recordPaymentMock = vi.fn();

vi.mock("./api", () => ({
  billingApi: {
    activeBills: (...args: unknown[]) => activeBillsMock(...args),
    recordPayment: (...args: unknown[]) => recordPaymentMock(...args),
  }
}));

describe("BillingDashboard", () => {
  it("renders active bills and displays totals", async () => {
    // We need to bypass the actual auth context or mock it so that role is cashier.
    // For simplicity, we'll mock the api to return the active bills.
    activeBillsMock.mockResolvedValueOnce([
      {
        id: "bill-1",
        human_id: "B-TEST",
        session: "session-1",
        status: "draft",
        grand_total: "300.00",
        paid_amount: "0.00",
        outstanding_amount: "300.00",
      },
    ]);

    const { AuthContext } = await import("../../auth/auth-context");
    render(
      <AuthContext.Provider
        value={{
          user: { id: 1, role: "cashier", username: "cashier", first_name: "a", last_name: "b", is_active: true, must_change_pin: false },
          status: "authenticated",
          loginPath: "/login/staff",
          loginOwner: vi.fn(),
          loginStaff: vi.fn(),
          logout: vi.fn(),
          refresh: vi.fn(),
          updateUser: vi.fn(),
        }}
      >
        <MemoryRouter>
          <BillingDashboard />
        </MemoryRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText("B-TEST")).toBeInTheDocument();
      const amounts = screen.getAllByText("NPR 300.00");
      expect(amounts.length).toBeGreaterThan(0);
    });
  });
});

describe("PaymentForm", () => {
  it("prevents submission of 0 or negative amount", async () => {
    const onSuccess = vi.fn();
    render(<PaymentForm billId="123" maxAmount={300} onPaymentSuccess={onSuccess} />);

    const amountInput = screen.getByLabelText(/Amount/i);
    const submitBtn = screen.getByRole("button", { name: /Record Payment/i });

    // Change to 0
    await userEvent.clear(amountInput);
    await userEvent.type(amountInput, "0");

    expect(submitBtn).toBeDisabled();
  });

  it("submits the correct payload", async () => {
    const onSuccess = vi.fn();
    recordPaymentMock.mockResolvedValueOnce({});

    render(<PaymentForm billId="123" maxAmount={300} onPaymentSuccess={onSuccess} />);

    const amountInput = screen.getByLabelText(/Amount/i);
    const submitBtn = screen.getByRole("button", { name: /Record Payment/i });

    await userEvent.clear(amountInput);
    await userEvent.type(amountInput, "150.00");

    expect(submitBtn).not.toBeDisabled();

    await userEvent.click(submitBtn);

    expect(recordPaymentMock).toHaveBeenCalledWith("123", expect.objectContaining({
      amount: 150.00,
      method: "cash"
    }));
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});

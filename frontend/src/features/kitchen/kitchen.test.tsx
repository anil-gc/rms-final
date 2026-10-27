import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { KitchenDashboard } from "./KitchenDashboard";
import { AuthProvider } from "../../auth/AuthProvider";

// Mock the API
const markPreparingMock = vi.fn().mockResolvedValue({});
const markReadyMock = vi.fn().mockResolvedValue({});
const markServedMock = vi.fn().mockResolvedValue({});
const ticketsMock = vi.fn().mockResolvedValue([
  {
    ticket_id: "1", order_line_id: 1, item_name: "Tea", quantity: 2,
    table_name: "Table 1", batch_sequence: 1, waiter_name: "waiter", approved_at: "2026-10-25T12:00:00Z", status: "pending"
  }
]);

vi.mock("./api", () => ({
  kitchenApi: {
    tickets: (...args) => ticketsMock(...args),
    markPreparing: (...args) => markPreparingMock(...args),
    markReady: (...args) => markReadyMock(...args),
    markServed: (...args) => markServedMock(...args),
  }
}));

describe("KitchenDashboard", () => {
  it("renders pending and status tabs", async () => {
    render(
      <AuthProvider>
        <KitchenDashboard />
      </AuthProvider>
    );
    expect(screen.getByText("Kitchen Display System")).toBeInTheDocument();

    // Wait for tickets to load
    await waitFor(() => {
      expect(screen.getByText("Table 1")).toBeInTheDocument();
      expect(screen.getByText("2x Tea")).toBeInTheDocument();
    });

    const btn = screen.getByText("Start Preparing");
    fireEvent.click(btn);

    await waitFor(() => {
      expect(markPreparingMock).toHaveBeenCalledWith(1);
    });
  });
});

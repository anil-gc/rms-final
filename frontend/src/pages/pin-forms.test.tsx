import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import type { ReactNode } from "react";
import { AuthContext } from "../auth/auth-context";
import type { AuthValue } from "../auth/auth-context";
import type { User } from "../types";
import { api } from "../lib/api";
import { LoginPage } from "./LoginPage";
import { CredentialForm } from "./ProfilePage";
import { StaffPage } from "./StaffPage";
import { TemporaryPinPage } from "./TemporaryPinPage";

vi.mock("../lib/api", async (original) => ({
  ...(await original<typeof import("../lib/api")>()),
  api: {
    staff: vi.fn(),
    createStaff: vi.fn(),
    resetPin: vi.fn(),
    changePin: vi.fn(),
    changePassword: vi.fn(),
  },
}));

const staff: User = {
  id: 2,
  username: "pin-test-staff",
  first_name: "",
  last_name: "",
  role: "waiter",
  is_active: true,
  must_change_pin: false,
};
function context(user: User | null = staff): AuthValue {
  return {
    user,
    status: user ? "authenticated" : "anonymous",
    loginPath: "/login/staff",
    refresh: vi.fn(),
    loginOwner: vi.fn(),
    loginStaff: vi.fn(),
    logout: vi.fn(),
    updateUser: vi.fn(),
  };
}
function mount(node: ReactNode, value = context()) {
  return render(
    <AuthContext.Provider value={value}>
      <MemoryRouter>{node}</MemoryRouter>
    </AuthContext.Provider>,
  );
}
function fourDigits(element: HTMLElement) {
  expect(element).toHaveAttribute("maxlength", "4");
  expect(element).toHaveAttribute("minlength", "4");
  expect(element).toHaveAttribute("pattern", "[0-9]{4}");
  expect(element).toHaveAttribute("inputmode", "numeric");
}

describe("four-digit staff credentials", () => {
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
    vi.mocked(api.staff).mockResolvedValue([staff]);
    vi.mocked(api.changePin).mockResolvedValue(staff);
    vi.mocked(api.createStaff).mockResolvedValue(staff);
    vi.mocked(api.resetPin).mockResolvedValue({
      ...staff,
      must_change_pin: true,
    });
  });

  it("logs in with four digits and preserves a leading zero", async () => {
    const value = context(null);
    vi.mocked(value.loginStaff).mockResolvedValue(staff);
    mount(<LoginPage kind="staff" />, value);
    const pin = screen.getByLabelText("PIN");
    fourDigits(pin);
    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: staff.username },
    });
    fireEvent.change(pin, { target: { value: "0427" } });
    fireEvent.click(
      screen.getByRole("button", { name: /Sign in to workspace/ }),
    );
    await waitFor(() =>
      expect(value.loginStaff).toHaveBeenCalledWith(staff.username, "0427"),
    );
    expect(pin).toHaveValue("");
  });

  it("offers legacy six-digit sign-in explicitly and clears input when switching", async () => {
    const value = context(null);
    vi.mocked(value.loginStaff).mockResolvedValue(staff);
    mount(<LoginPage kind="staff" />, value);
    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: staff.username },
    });
    const pin = screen.getByLabelText("PIN");
    fireEvent.change(pin, { target: { value: "0427" } });
    fireEvent.click(
      screen.getByRole("checkbox", { name: /existing 6-digit PIN/ }),
    );
    expect(pin).toHaveValue("");
    expect(pin).toHaveAttribute("maxlength", "6");
    fireEvent.change(pin, { target: { value: "042759" } });
    fireEvent.click(
      screen.getByRole("button", { name: /Sign in to workspace/ }),
    );
    await waitFor(() =>
      expect(value.loginStaff).toHaveBeenCalledWith(staff.username, "042759"),
    );
  });

  it.each(["123", "12345", "12a4"])(
    "blocks invalid login input %s before sending",
    (pin) => {
      const value = context(null);
      mount(<LoginPage kind="staff" />, value);
      fireEvent.change(screen.getByLabelText("Username"), {
        target: { value: staff.username },
      });
      fireEvent.change(screen.getByLabelText("PIN"), {
        target: { value: pin },
      });
      expect(
        (screen.getByLabelText("PIN") as HTMLInputElement).checkValidity(),
      ).toBe(false);
      fireEvent.click(
        screen.getByRole("button", { name: /Sign in to workspace/ }),
      );
      expect(value.loginStaff).not.toHaveBeenCalled();
    },
  );

  it("creates staff with a four-digit temporary PIN as a string", async () => {
    mount(<StaffPage />, context({ ...staff, role: "owner" }));
    fireEvent.click(screen.getByRole("button", { name: "Add staff member" }));
    const dialog = screen.getByRole("dialog");
    const pin = within(dialog).getByLabelText("Temporary PIN");
    fourDigits(pin);
    fireEvent.change(within(dialog).getByLabelText("Staff username"), {
      target: { value: "new-test-staff" },
    });
    fireEvent.change(pin, { target: { value: "0427" } });
    fireEvent.change(within(dialog).getByLabelText("Your Owner password"), {
      target: { value: "synthetic-owner-password" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Add staff member" }),
    );
    await waitFor(() =>
      expect(api.createStaff).toHaveBeenCalledWith(
        expect.objectContaining({ pin: "0427" }),
      ),
    );
  });

  it("resets staff using a new four-digit temporary PIN", async () => {
    mount(<StaffPage />, context({ ...staff, role: "owner" }));
    fireEvent.click(
      (
        await screen.findAllByRole("button", {
          name: `Reset PIN for ${staff.username}`,
        })
      )[0],
    );
    const dialog = screen.getByRole("dialog");
    fourDigits(within(dialog).getByLabelText("Temporary PIN"));
    fireEvent.change(within(dialog).getByLabelText("Temporary PIN"), {
      target: { value: "0427" },
    });
    fireEvent.change(within(dialog).getByLabelText("Your Owner password"), {
      target: { value: "synthetic-owner-password" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Reset PIN" }));
    await waitFor(() =>
      expect(api.resetPin).toHaveBeenCalledWith(
        staff.id,
        "0427",
        "synthetic-owner-password",
      ),
    );
  });

  it("changes a legacy current PIN to four digits without truncation", async () => {
    mount(<CredentialForm />);
    fourDigits(screen.getByLabelText("Current PIN"));
    fourDigits(screen.getByLabelText("New PIN"));
    fourDigits(screen.getByLabelText("Confirm new PIN"));
    fireEvent.click(
      screen.getByRole("checkbox", { name: /still has 6 digits/ }),
    );
    expect(screen.getByLabelText("Current PIN")).toHaveAttribute(
      "maxlength",
      "6",
    );
    fourDigits(screen.getByLabelText("New PIN"));
    fireEvent.change(screen.getByLabelText("Current PIN"), {
      target: { value: "482759" },
    });
    fireEvent.change(screen.getByLabelText("New PIN"), {
      target: { value: "0427" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new PIN"), {
      target: { value: "0427" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Update PIN/ }));
    await waitFor(() =>
      expect(api.changePin).toHaveBeenCalledWith("482759", "0427"),
    );
    fourDigits(screen.getByLabelText("Current PIN"));
  });

  it("uses four digits for required temporary-PIN replacement", () => {
    mount(<TemporaryPinPage />, context({ ...staff, must_change_pin: true }));
    fourDigits(screen.getByLabelText("Temporary PIN"));
    fourDigits(screen.getByLabelText("New PIN"));
    fourDigits(screen.getByLabelText("Confirm new PIN"));
  });

  it("keeps Owner password inputs and authentication unchanged", async () => {
    const value = context(null);
    vi.mocked(value.loginOwner).mockResolvedValue({ ...staff, role: "owner" });
    mount(<LoginPage kind="owner" />, value);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toHaveAttribute(
      "maxlength",
      "1024",
    );
    expect(screen.getByLabelText("Password")).not.toHaveAttribute("pattern");
    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "owner-test" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "synthetic-owner-password" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /Sign in to workspace/ }),
    );
    await waitFor(() =>
      expect(value.loginOwner).toHaveBeenCalledWith(
        "owner-test",
        "synthetic-owner-password",
      ),
    );
  });
});

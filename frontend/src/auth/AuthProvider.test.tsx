import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./AuthProvider";
import { useAuth } from "./auth-context";
import { api, ApiError } from "../lib/api";
import type { User } from "../types";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  api: {
    me: vi.fn(),
    ownerLogin: vi.fn(),
    staffLogin: vi.fn(),
    logout: vi.fn(),
  },
}));
const user: User = {
  id: 1,
  username: "test.owner",
  first_name: "",
  last_name: "",
  role: "owner",
  is_active: true,
  must_change_pin: false,
};
function Probe() {
  const auth = useAuth();
  return (
    <>
      <div data-testid="session">
        {auth.status}:{auth.user?.username || "none"}
      </div>
      <button
        onClick={() => void auth.loginOwner("test.owner", "test-only-password")}
      >
        Log in
      </button>
      <button onClick={() => void auth.logout().catch(() => undefined)}>
        Log out
      </button>
    </>
  );
}
describe("session reconciliation", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal("BroadcastChannel", undefined);
  });
  afterEach(() => vi.unstubAllGlobals());
  it("does not let an earlier anonymous probe overwrite a successful login", async () => {
    let rejectProbe: (reason: unknown) => void = () => undefined;
    vi.mocked(api.me).mockImplementation(
      () =>
        new Promise((_resolve, reject) => {
          rejectProbe = reject;
        }),
    );
    vi.mocked(api.ownerLogin).mockResolvedValue({ user, csrf_token: "test" });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    fireEvent.click(screen.getByText("Log in"));
    await waitFor(() =>
      expect(screen.getByTestId("session")).toHaveTextContent(
        "authenticated:test.owner",
      ),
    );
    await act(async () => {
      rejectProbe(new ApiError("Forbidden", 403));
    });
    expect(screen.getByTestId("session")).toHaveTextContent(
      "authenticated:test.owner",
    );
  });
  it("rechecks identity on a forbidden action instead of blindly logging out", async () => {
    vi.mocked(api.me).mockResolvedValue(user);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("session")).toHaveTextContent(
        "authenticated:test.owner",
      ),
    );
    await act(async () => {
      window.dispatchEvent(new Event("rms:check-session"));
    });
    expect(api.me).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId("session")).toHaveTextContent(
      "authenticated:test.owner",
    );
  });
  it("removes an actually expired or revoked session after the identity check", async () => {
    vi.mocked(api.me)
      .mockResolvedValueOnce(user)
      .mockRejectedValue(new ApiError("Forbidden", 403));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("session")).toHaveTextContent(
        "authenticated:test.owner",
      ),
    );
    await act(async () => {
      window.dispatchEvent(new Event("rms:check-session"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("session")).toHaveTextContent("anonymous:none"),
    );
  });
  it("does not report a successful logout when the server could not be reached", async () => {
    vi.mocked(api.me).mockResolvedValue(user);
    vi.mocked(api.logout).mockRejectedValue(new ApiError("Offline", 0));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("session")).toHaveTextContent(
        "authenticated:test.owner",
      ),
    );
    await act(async () => {
      fireEvent.click(screen.getByText("Log out"));
    });
    expect(screen.getByTestId("session")).toHaveTextContent(
      "authenticated:test.owner",
    );
  });
});

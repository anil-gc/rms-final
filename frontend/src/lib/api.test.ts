import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

const profile = {
  id: 1,
  username: "test.owner",
  first_name: "",
  last_name: "",
  role: "owner",
  is_active: true,
  must_change_pin: false,
};
const json = (body: unknown, status = 200, headers = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });

describe("session API client", () => {
  beforeEach(() => {
    vi.resetModules();
    localStorage.clear();
    sessionStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("bootstraps CSRF, adopts the rotated login token, and sends cookies without persistent credentials", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json({ csrf_token: "test-before-login" }))
      .mockResolvedValueOnce(
        json({ user: profile, csrf_token: "test-after-login" }),
      )
      .mockResolvedValueOnce(json({ ...profile, id: 2, role: "waiter" }, 201));
    vi.stubGlobal("fetch", fetchMock);
    const { api } = await import("./api");
    await api.ownerLogin("test.owner", "test-only-password");
    await api.createStaff({
      username: "test.staff",
      first_name: "",
      last_name: "",
      role: "waiter",
      pin: "482759",
      owner_password: "test-only-password",
    });
    expect(fetchMock.mock.calls[1][1].headers["X-CSRFToken"]).toBe(
      "test-before-login",
    );
    expect(fetchMock.mock.calls[2][1].headers["X-CSRFToken"]).toBe(
      "test-after-login",
    );
    for (const [url, options] of fetchMock.mock.calls) {
      expect(url).toMatch(/^\/api\/v1\/accounts\//);
      expect(options.credentials).toBe("include");
    }
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("does not automatically replay a failed write, and refreshes CSRF for the next manual attempt", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json({ csrf_token: "old-test-token" }))
      .mockResolvedValueOnce(json({ detail: "CSRF validation failed." }, 403))
      .mockResolvedValueOnce(json({ csrf_token: "new-test-token" }))
      .mockResolvedValueOnce(json(profile));
    vi.stubGlobal("fetch", fetchMock);
    const { api, ApiError } = await import("./api");
    await expect(api.changePin("482759", "739284")).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
    await api.changePin("482759", "739284");
    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(fetchMock.mock.calls[3][1].headers["X-CSRFToken"]).toBe(
      "new-test-token",
    );
  });

  it("keeps backend field validation and Retry-After available to the form", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json({ csrf_token: "test" }))
        .mockResolvedValueOnce(
          json(
            {
              detail: "Too many attempts.",
              new_pin: ["Choose a different PIN."],
            },
            429,
            { "Retry-After": "120" },
          ),
        ),
    );
    const { api } = await import("./api");
    await expect(api.changePin("482759", "739284")).rejects.toMatchObject({
      status: 429,
      retryAfter: 120,
      fields: { new_pin: "Choose a different PIN." },
    });
  });

  it("distinguishes connection failure from an invalid session", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Network unavailable")),
    );
    const { api } = await import("./api");
    await expect(api.me()).rejects.toMatchObject({ status: 0 });
  });

  it("coalesces concurrent CSRF bootstraps", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(json({ csrf_token: "shared-test-token" }));
    vi.stubGlobal("fetch", fetchMock);
    const { ensureCsrf } = await import("./api");
    await Promise.all([ensureCsrf(), ensureCsrf(), ensureCsrf()]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

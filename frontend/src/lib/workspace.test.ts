import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("workspace transport", () => {
  beforeEach(() => vi.resetModules());
  afterEach(() => vi.unstubAllGlobals());

  it("sends logo multipart with CSRF and cookies while letting the browser supply the boundary", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json({ csrf_token: "synthetic-csrf" }))
      .mockResolvedValueOnce(
        json({ id: 1, logo_url: "/api/v1/restaurant/logo/" }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const { workspace } = await import("./workspace");
    await workspace.uploadLogo(
      new File(["synthetic-file"], "logo.png", { type: "image/png" }),
    );
    const [url, request] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/v1/restaurant/logo/");
    expect(request.credentials).toBe("include");
    expect(request.headers["X-CSRFToken"]).toBe("synthetic-csrf");
    expect(request.headers["Content-Type"]).toBeUndefined();
    expect(request.body).toBeInstanceOf(FormData);
    expect(request.body.get("logo").name).toBe("logo.png");
  });

  it("treats only restaurant 404 as unconfigured and preserves connection/permission errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json({}, 404))
        .mockResolvedValueOnce(json({ detail: "Forbidden" }, 403))
        .mockRejectedValueOnce(new TypeError("offline")),
    );
    const { workspace } = await import("./workspace");
    expect(await workspace.restaurant()).toBeNull();
    await expect(workspace.restaurant()).rejects.toMatchObject({ status: 403 });
    await expect(workspace.restaurant()).rejects.toMatchObject({ status: 0 });
  });

  it("keeps prices as decimal strings and uses actual versioned module paths", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json({ csrf_token: "synthetic-csrf" }))
      .mockResolvedValueOnce(json({ id: 7 }));
    vi.stubGlobal("fetch", fetchMock);
    const { workspace } = await import("./workspace");
    await workspace.saveItem(
      {
        name: "Test dish",
        category: 2,
        price: "250.75",
        description: "",
        is_available: true,
        is_active: true,
      },
      7,
    );
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/menu/items/7/");
    expect(fetchMock.mock.calls[1][1].method).toBe("PATCH");
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).price).toBe("250.75");
  });
});

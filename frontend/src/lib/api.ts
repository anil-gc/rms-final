import type { LoginResponse, StaffInput, User } from "../types";

export class ApiError extends Error {
  status: number;
  fields: Record<string, string>;
  retryAfter: number;
  constructor(
    message: string,
    status: number,
    fields: Record<string, string> = {},
    retryAfter = 0,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fields = fields;
    this.retryAfter = retryAfter;
  }
}

// Only the masked CSRF value is kept here. Credentials/session cookies are never read or persisted.
let csrfToken: string | null = null;
let csrfPending: Promise<string> | null = null;
export function invalidateCsrf() {
  csrfToken = null;
}

async function readBody(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  if (!response.headers.get("content-type")?.includes("application/json"))
    return null;
  return response.json().catch(() => null);
}

function makeError(response: Response, payload: unknown) {
  const fields: Record<string, string> = {};
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    for (const [key, value] of Object.entries(payload)) {
      if (typeof value === "string") fields[key] = value;
      else if (Array.isArray(value))
        fields[key] = value
          .filter((item) => typeof item === "string")
          .join(" ");
    }
  }
  const messages: Record<number, string> = {
    400: "Please check the highlighted details.",
    401: "The credentials could not be verified.",
    403: "Your session or access may have changed. Please try again.",
    404: "The requested record could not be found. Refresh and try again.",
    429: "Too many attempts. Please wait before trying again.",
  };
  let message =
    fields.detail ||
    fields.non_field_errors ||
    messages[response.status] ||
    "The request could not be completed. Please try again.";
  if (message.toLowerCase().includes("csrf")) {
    invalidateCsrf();
    message = "Your security token changed. Please submit again.";
  }
  const seconds = Number(response.headers.get("retry-after"));
  const retryAfter =
    Number.isFinite(seconds) && seconds > 0
      ? Math.ceil(seconds)
      : response.status === 429
        ? 60
        : 0;
  return new ApiError(message, response.status, fields, retryAfter);
}

async function fetchApi(
  path: string,
  init: RequestInit = {},
  prefix = "accounts/",
) {
  try {
    return await fetch(`/api/v1/${prefix}${path}`, {
      ...init,
      credentials: "include",
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "We couldn’t connect. Check your connection and try again.",
      0,
    );
  }
}

export async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  if (!csrfPending) {
    csrfPending = (async () => {
      const response = await fetchApi("csrf/");
      const body = await readBody(response);
      if (!response.ok) throw makeError(response, body);
      if (
        !body ||
        typeof body !== "object" ||
        !("csrf_token" in body) ||
        typeof body.csrf_token !== "string"
      ) {
        throw new ApiError(
          "A secure connection could not be prepared. Please try again.",
          0,
        );
      }
      csrfToken = body.csrf_token;
      return csrfToken;
    })().finally(() => {
      csrfPending = null;
    });
  }
  return csrfPending;
}

async function request<T>(
  path: string,
  method = "GET",
  data?: unknown,
  notify = true,
  prefix = "accounts/",
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    headers["X-CSRFToken"] = await ensureCsrf();
    if (!(data instanceof FormData))
      headers["Content-Type"] = "application/json";
  }
  const response = await fetchApi(
    path,
    {
      method,
      headers,
      ...(data === undefined
        ? {}
        : { body: data instanceof FormData ? data : JSON.stringify(data) }),
    },
    prefix,
  );
  const body = await readBody(response);
  if (!response.ok) {
    const error = makeError(response, body);
    // A permission/CSRF 403 is NOT proof of logout. The provider rechecks /me/.
    if (response.status === 403 && notify)
      window.dispatchEvent(new Event("rms:check-session"));
    throw error;
  }
  if (
    body &&
    typeof body === "object" &&
    "csrf_token" in body &&
    typeof body.csrf_token === "string"
  )
    csrfToken = body.csrf_token;
  return body as T;
}

export const api = {
  me: () => request<User>("me/", "GET", undefined, false),
  ownerLogin: (username: string, password: string) =>
    request<LoginResponse>(
      "login/owner/",
      "POST",
      { username, password },
      false,
    ),
  staffLogin: (username: string, pin: string) =>
    request<LoginResponse>("login/staff/", "POST", { username, pin }, false),
  logout: () => request<void>("logout/", "POST", {}),
  staff: () => request<User[]>("staff/"),
  createStaff: (data: StaffInput) => request<User>("staff/", "POST", data),
  resetPin: (id: number, new_pin: string, owner_password: string) =>
    request<User>(`staff/${id}/pin/reset/`, "POST", {
      new_pin,
      owner_password,
    }),
  setActive: (id: number, is_active: boolean, owner_password: string) =>
    request<User>(`staff/${id}/`, "PATCH", { is_active, owner_password }),
  changePin: (current_pin: string, new_pin: string) =>
    request<User>("pin/change/", "POST", { current_pin, new_pin }),
  changePassword: (current_password: string, new_password: string) =>
    request<User>("password/change/", "POST", {
      current_password,
      new_password,
    }),
};

// Workspace modules share the existing session/CSRF transport, including uploads.
export function workspaceRequest<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  return request<T>(path, method, data, true, "");
}

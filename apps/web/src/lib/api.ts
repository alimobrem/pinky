const BASE_URL = "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class SessionExpiredError extends ApiError {
  constructor(message = "Session expired") {
    super(message, 401);
    this.name = "SessionExpiredError";
  }
}

export class ClusterBindingError extends ApiError {
  constructor(message: string) {
    super(message, 401);
    this.name = "ClusterBindingError";
  }
}

export class ForbiddenError extends ApiError {
  constructor(message: string) {
    super(message, 403);
    this.name = "ForbiddenError";
  }
}

function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const csrf = getCsrfToken();
  if (csrf && method !== "GET") {
    headers["X-CSRF-Token"] = csrf;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const text = await res.text().catch(() => "");
  let message = `${res.status} ${res.statusText}`;
  try {
    const err = JSON.parse(text);
    if (err.error?.message) message = err.error.message;
    else if (err.detail) message = err.detail;
  } catch {
    if (text) message = text;
  }

  if (res.status === 401) {
    const lower = message.toLowerCase();
    const isBindingIssue =
      lower.includes("binding") ||
      lower.includes("reauthentication required") ||
      lower.includes("cluster access");
    if (!isBindingIssue && typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw isBindingIssue ? new ClusterBindingError(message) : new SessionExpiredError(message);
  }

  if (res.status === 403) {
    throw new ForbiddenError(message);
  }

  if (!res.ok) {
    throw new ApiError(message, res.status);
  }

  if (res.status === 204) return undefined as T;
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  del: (path: string) => request<void>("DELETE", path),
};

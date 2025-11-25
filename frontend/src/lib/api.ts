import { auth } from "./auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

function buildUrl(path: string) {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  if (!path.startsWith("/")) {
    return `${API_BASE_URL}/${path}`;
  }

  return `${API_BASE_URL}${path}`;
}

function extractErrorMessage(payload: any, fallback: string) {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;

  // FastAPI often sends {detail: "..."} or {detail: [{msg: "..."}]}
  const fromDetail = (detail: any): string | undefined => {
    if (!detail) return undefined;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((d) => {
          if (typeof d === "string") return d;
          if (d?.msg) return d.msg;
          if (d?.message) return d.message;
          return undefined;
        })
        .filter(Boolean)
        .join("; ");
      return msgs || undefined;
    }
    if (typeof detail === "object") {
      return detail.message || detail.error || detail.msg;
    }
    return undefined;
  };

  if (typeof payload === "object") {
    const detailMsg = fromDetail(payload.detail);
    if (detailMsg) return detailMsg;

    const direct =
      payload.message || payload.error || payload.msg || payload.title;
    if (direct) return direct;

    try {
      return JSON.stringify(payload);
    } catch {
      return fallback;
    }
  }

  return fallback;
}

async function refreshAccessToken(): Promise<string | null> {
  try {
    const res = await fetch(buildUrl("/auth/refresh"), {
      method: "POST",
      credentials: "include",
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) return null;
    const accessToken = data?.access_token;
    if (!accessToken) return null;
    auth.setSession({ accessToken, refreshToken: data?.refresh_token });
    return accessToken;
  } catch {
    return null;
  }
}

async function apiFetchInternal(
  path: string,
  options: RequestInit = {},
): Promise<any> {
  const url = buildUrl(path);

  const headers = new Headers(options.headers || {});
  let token = auth.getToken();

  // If no token yet but we might have a refresh cookie, try to refresh before the first call
  if (!token && !headers.has("Authorization")) {
    token = await refreshAccessToken();
  }

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  async function doFetch(currentHeaders: Headers): Promise<Response> {
    return fetch(url, { ...options, headers: currentHeaders, credentials: "include" });
  }

  let response: Response;
  try {
    response = await doFetch(headers);
  } catch (err: any) {
    throw new Error(
      err?.message || "네트워크 요청에 실패했습니다. 백엔드 서버를 확인해주세요.",
    );
  }

  // If unauthorized due to missing/expired token, try refresh once then retry
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers.set("Authorization", `Bearer ${refreshed}`);
      response = await doFetch(headers);
    } else if (token) {
      // Token existed but server still says 401; fall back to retrying once more with current token.
      headers.set("Authorization", `Bearer ${token}`);
      response = await doFetch(headers);
    }
  }

  const text = await response.text();
  let data: any = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const message = extractErrorMessage(
      data,
      response.statusText || "요청에 실패했습니다.",
    );
    const safeMessage =
      typeof message === "string"
        ? message
        : (() => {
            try {
              return JSON.stringify(message);
            } catch {
              return "요청에 실패했습니다.";
            }
          })();

    const error: any = new Error(safeMessage);
    error.status = response.status;
    error.payload = data;
    throw error;
  }

  return data;
}

/**
 * Public API helper that always attaches Authorization (if available) and
 * auto-refreshes on 401. Use this for all backend calls.
 */
export function api(path: string, options: RequestInit = {}) {
  return apiFetchInternal(path, options);
}

// Backward compatibility alias
export const apiFetch = api;

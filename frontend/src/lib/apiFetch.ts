import { auth } from "./auth";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type FetchDebug = {
  url: string;
  method: string;
  status?: number;
  hasAuth: boolean;
  bodySnippet?: string;
};

let refreshPromise: Promise<string | null> | null = null;

function buildUrl(path: string) {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (!path.startsWith("/")) return `${API_BASE_URL}/${path}`;
  return `${API_BASE_URL}${path}`;
}

function getResponseErrorMessage(text: string, fallback: string): string {
  if (!text) return fallback;
  try {
    const payload = JSON.parse(text);
    const detail = payload?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (detail && typeof detail === "object") {
      const message = detail.message || detail.error || detail.msg;
      if (typeof message === "string" && message.trim()) return message;
    }
    const message = payload?.message || payload?.error || payload?.msg;
    if (typeof message === "string" && message.trim()) return message;
  } catch {
    // Plain-text backend responses are already suitable for display.
  }
  return text.slice(0, 300) || fallback;
}

export async function refreshBackendAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  const request = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        auth.clear();
        return null;
      }
      const data = await response.json();
      const token = data?.access_token || null;
      if (token) auth.setToken(token);
      return token;
    } catch {
      return null;
    }
  })();
  refreshPromise = request;
  try {
    return await request;
  } finally {
    if (refreshPromise === request) refreshPromise = null;
  }
}

export async function getSupabaseToken(): Promise<string | null> {
  return auth.getToken() || refreshBackendAccessToken();
}

export async function apiFetch(
  path: string,
  options: Omit<RequestInit, "body"> & { body?: any } = {},
  token?: string | null,
  onDebug?: (info: FetchDebug) => void,
) {
  const method = (options.method || "GET").toUpperCase();
  const url = buildUrl(path);

  // Prefer the newest in-memory token. Components may still hold the token
  // that was current before a refresh completed.
  let accessToken = auth.getToken() || token || (await getSupabaseToken());
  if (!accessToken) {
    const err: any = new Error("NO_TOKEN");
    err.code = "NO_TOKEN";
    throw err;
  }

  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Authorization", `Bearer ${accessToken}`);

  const body =
    options.body && typeof options.body !== "string"
      ? JSON.stringify(options.body)
      : options.body;

  const send = async () => {
    try {
      return await fetch(url, {
        ...options,
        method,
        headers,
        body,
        credentials: "include",
      });
    } catch (cause) {
      const err: any = new Error(
        `백엔드에 연결할 수 없습니다 (${API_BASE_URL}). 백엔드 서버가 실행 중인지 확인하세요.`,
      );
      err.code = "BACKEND_UNREACHABLE";
      err.cause = cause;
      throw err;
    }
  };

  let res = await send();
  if (res.status === 401) {
    const refreshedToken = await refreshBackendAccessToken();
    if (refreshedToken) {
      accessToken = refreshedToken;
      headers.set("Authorization", `Bearer ${accessToken}`);
      res = await send();
    }
  }

  const text = await res.text();
  const snippet = text.slice(0, 300);
  onDebug?.({ url, method, status: res.status, hasAuth: true, bodySnippet: snippet });

  if (!res.ok) {
    const message = getResponseErrorMessage(
      text,
      res.statusText || "요청에 실패했습니다.",
    );
    const err: any = new Error(message);
    err.status = res.status;
    err.bodySnippet = snippet;
    if (res.status === 401) {
      err.code = "NO_TOKEN";
    }
    throw err;
  }

  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return text as any;
  }
}

import { auth } from "./auth";
import { API_BASE_URL, getSupabaseToken } from "./apiFetch";

function buildUrl(path: string) {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (!path.startsWith("/")) return `${API_BASE_URL}/${path}`;
  return `${API_BASE_URL}${path}`;
}

export type DebugInfo = {
  url: string;
  method: string;
  status?: number;
  bodySnippet?: string;
  hasAuth?: boolean;
  threadId?: string;
};

async function getAccessToken(): Promise<string | null> {
  const stored = auth.getToken();
  if (stored) return stored;
  return getSupabaseToken();
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (Array.isArray(payload)) {
    return payload
      .map((p) => extractErrorMessage(p, ""))
      .filter(Boolean)
      .join("; ");
  }
  if (typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    const direct =
      obj.detail ??
      obj.message ??
      obj.error ??
      obj.msg ??
      obj.title;
    if (typeof direct === "string" && direct.trim()) {
      return direct;
    }
    if (direct != null) {
      try {
        return JSON.stringify(direct);
      } catch {
        return fallback;
      }
    }
    return (
      (() => {
        try {
          return JSON.stringify(obj);
        } catch {
          return fallback;
        }
      })()
    );
  }
  return fallback;
}

async function refreshToken(): Promise<string | null> {
  auth.clear();
  return getSupabaseToken();
}

export async function apiClient(
  path: string,
  options: RequestInit = {},
  debug?: (info: DebugInfo) => void,
  meta?: { threadId?: string },
) {
  const url = buildUrl(path);
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const token = headers.get("Authorization")?.replace(/^Bearer\s+/i, "") || (await getAccessToken());
  const hasAuth = !!token;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  else {
    const notLoggedIn: any = new Error("Not logged in");
    notLoggedIn.status = 401;
    if (typeof window !== "undefined") {
      window.location.replace("/login");
    }
    throw notLoggedIn;
  }

  async function doFetch(currentHeaders: Headers) {
    return fetch(url, { ...options, headers: currentHeaders, credentials: "include" });
  }

  let response = await doFetch(headers);

  if (response.status === 401) {
    const refreshed = await refreshToken();
    if (refreshed) {
      headers.set("Authorization", `Bearer ${refreshed}`);
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

  const snippet = typeof data === "string" ? data.slice(0, 500) : JSON.stringify(data).slice(0, 500);
  debug?.({ url, method, status: response.status, bodySnippet: snippet, hasAuth, threadId: meta?.threadId });

  if (!response.ok) {
    const message = extractErrorMessage(data, response.statusText || "요청에 실패했습니다.");
    const error: any = new Error(message);
    error.status = response.status;
    error.payload = data;
    error.bodySnippet = snippet;
    error.hasAuth = hasAuth;
    error.threadId = meta?.threadId;
    if (response.status === 401 && typeof window !== "undefined") {
      window.location.replace("/login");
    }
    throw error;
  }

  return data;
}

export async function pingBackend(debug?: (info: DebugInfo) => void) {
  try {
    const res = await fetch(buildUrl("/"));
    const text = await res.text();
    debug?.({
      url: buildUrl("/"),
      method: "GET",
      status: res.status,
      bodySnippet: text.slice(0, 200),
      hasAuth: false,
    });
    return res.ok;
  } catch (e: any) {
    debug?.({
      url: buildUrl("/"),
      method: "GET",
      status: undefined,
      bodySnippet: e?.message,
      hasAuth: false,
    });
    return false;
  }
}

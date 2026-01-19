import { auth } from "./auth";
import { supabase } from "./supabaseClient";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL ||
  "http://127.0.0.1:8000";

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

  // Supabase session fallback (auto-refreshes if needed)
  const sessionRes = await supabase.auth.getSession();
  const token = sessionRes.data.session?.access_token || null;
  const refresh = sessionRes.data.session?.refresh_token || null;
  if (token) {
    auth.setSession({ accessToken: token, refreshToken: refresh || undefined });
  }
  return token;
}

function extractErrorMessage(payload: any, fallback: string) {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (Array.isArray(payload)) return payload.map((p) => extractErrorMessage(p, "")).filter(Boolean).join("; ");
  if (typeof payload === "object") {
    return (
      payload.detail ||
      payload.message ||
      payload.error ||
      payload.msg ||
      payload.title ||
      (() => {
        try {
          return JSON.stringify(payload);
        } catch {
          return fallback;
        }
      })()
    );
  }
  return fallback;
}

async function refreshToken(): Promise<string | null> {
  try {
    const res = await supabase.auth.refreshSession();
    const token = res.data.session?.access_token || null;
    const refresh = res.data.session?.refresh_token || null;
    if (token) {
      auth.setSession({ accessToken: token, refreshToken: refresh || undefined });
    }
    return token;
  } catch {
    return null;
  }
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

  let token = headers.get("Authorization")?.replace(/^Bearer\s+/i, "") || (await getAccessToken());
  const hasAuth = !!token;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  else {
    const notLoggedIn: any = new Error("Not logged in");
    notLoggedIn.status = 401;
    if (typeof window !== "undefined") {
      window.location.href = "/login";
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
  if (process.env.NODE_ENV !== "production") {
    console.warn("[apiClient]", method, url, "->", response.status, {
      hasAuth,
      threadId: meta?.threadId,
      body: snippet,
    });
  }
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
      window.location.href = "/login";
    }
    throw error;
  }

  return data;
}

export async function pingBackend(debug?: (info: DebugInfo) => void) {
  try {
    const res = await fetch(buildUrl("/openapi.json"));
    const text = await res.text();
    debug?.({
      url: buildUrl("/openapi.json"),
      method: "GET",
      status: res.status,
      bodySnippet: text.slice(0, 200),
      hasAuth: false,
    });
    return res.ok;
  } catch (e: any) {
    debug?.({
      url: buildUrl("/openapi.json"),
      method: "GET",
      status: undefined,
      bodySnippet: e?.message,
      hasAuth: false,
    });
    return false;
  }
}

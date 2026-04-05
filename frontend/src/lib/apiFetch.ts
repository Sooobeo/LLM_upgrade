import { auth } from "./auth";
import { supabase } from "./supabaseClient";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL ||
  "http://127.0.0.1:8000";

export type FetchDebug = {
  url: string;
  method: string;
  status?: number;
  hasAuth: boolean;
  bodySnippet?: string;
};

function buildUrl(path: string) {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (!path.startsWith("/")) return `${API_BASE}/${path}`;
  return `${API_BASE}${path}`;
}

export async function getSupabaseToken(): Promise<string | null> {
  const local = auth.getToken();
  if (local) return local;
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token || null;
  if (token) {
    auth.setSession({
      accessToken: token,
      refreshToken: data.session?.refresh_token || undefined,
    });
  }
  return token;
}

export async function apiFetch(
  path: string,
  options: Omit<RequestInit, "body"> & { body?: any } = {},
  token?: string | null,
  onDebug?: (info: FetchDebug) => void,
) {
  const method = (options.method || "GET").toUpperCase();
  const url = buildUrl(path);

  const accessToken = token ?? (await getSupabaseToken());
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

  const res = await fetch(url, {
    ...options,
    method,
    headers,
    body,
  });

  const text = await res.text();
  const snippet = text.slice(0, 300);
  onDebug?.({ url, method, status: res.status, hasAuth: true, bodySnippet: snippet });

  if (!res.ok) {
    const err: any = new Error(`Request failed (${res.status}): ${snippet || res.statusText}`);
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

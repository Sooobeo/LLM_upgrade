import { auth } from "./auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

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

  if (typeof payload === "object") {
    return (
      payload.detail ||
      payload.message ||
      payload.error ||
      payload.msg ||
      fallback
    );
  }

  return fallback;
}

export async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<any> {
  const url = buildUrl(path);

  const headers = new Headers(options.headers || {});
  const token = auth.getToken();

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch (err: any) {
    throw new Error(
      err?.message || "네트워크 요청에 실패했습니다. 백엔드 서버를 확인해주세요.",
    );
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
    throw new Error(typeof message === "string" ? message : String(message));
  }

  return data;
}

export const api = apiFetch;

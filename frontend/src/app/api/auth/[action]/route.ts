import { NextRequest, NextResponse } from "next/server";

const BACKEND_API_BASE_URL = (
  process.env.BACKEND_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://llm-upgrade.onrender.com"
    : "http://127.0.0.1:8000")
).replace(/\/+$/, "");

const AUTH_PATHS: Record<string, string> = {
  "google-session": "/auth/google/set-session",
  refresh: "/auth/refresh",
  password: "/auth/login/password",
  signup: "/auth/signup/password",
  logout: "/auth/logout",
};

function isTrustedRequest(request: NextRequest) {
  const origin = request.headers.get("origin");
  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite === "cross-site") return false;
  if (!origin) return true;

  try {
    const originHost = new URL(origin).host;
    const requestHosts = [
      request.headers.get("x-forwarded-host"),
      request.headers.get("host"),
      request.nextUrl.host,
    ].filter(Boolean);
    return requestHosts.includes(originHost);
  } catch {
    return false;
  }
}

function asHostOnlyCookie(setCookie: string) {
  const withoutDomain = setCookie.replace(/;\s*Domain=[^;]*/gi, "");
  const withoutSameSite = withoutDomain.replace(/;\s*SameSite=[^;]*/gi, "");
  return `${withoutSameSite}; SameSite=Lax`;
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ action: string }> },
) {
  if (!isTrustedRequest(request)) {
    return NextResponse.json(
      {
        detail: {
          code: "UNTRUSTED_ORIGIN",
          message: "Request origin is not allowed.",
        },
      },
      { status: 403 },
    );
  }

  const { action } = await context.params;
  const backendPath = AUTH_PATHS[action];
  if (!backendPath) {
    return NextResponse.json(
      { detail: { code: "NOT_FOUND", message: "Unknown auth action." } },
      { status: 404 },
    );
  }

  const requestBody = await request.text();
  const headers = new Headers();
  if (requestBody) {
    headers.set(
      "Content-Type",
      request.headers.get("content-type") || "application/json",
    );
  }

  const authorization = request.headers.get("authorization");
  if (authorization) headers.set("Authorization", authorization);

  const refreshToken = request.cookies.get("refresh_token")?.value;
  if (refreshToken) {
    headers.set("Cookie", `refresh_token=${refreshToken}`);
  }

  try {
    const backendResponse = await fetch(
      `${BACKEND_API_BASE_URL}${backendPath}`,
      {
        method: "POST",
        headers,
        body: requestBody || undefined,
        cache: "no-store",
      },
    );
    const responseBody = await backendResponse.text();
    const response = new NextResponse(responseBody, {
      status: backendResponse.status,
      headers: {
        "Cache-Control": "no-store",
        "Content-Type":
          backendResponse.headers.get("content-type") || "application/json",
      },
    });

    const setCookie = backendResponse.headers.get("set-cookie");
    if (setCookie) {
      response.headers.append("Set-Cookie", asHostOnlyCookie(setCookie));
    }
    return response;
  } catch {
    return NextResponse.json(
      {
        detail: {
          code: "AUTH_BACKEND_UNREACHABLE",
          message: "인증 서버에 연결할 수 없습니다.",
        },
      },
      { status: 502 },
    );
  }
}

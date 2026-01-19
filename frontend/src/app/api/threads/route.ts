// Proxy for /api/threads (dev only). Requires Authorization to be forwarded as-is.
import { NextRequest, NextResponse } from "next/server";

const BACKEND_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL ||
  process.env.BACKEND_API_BASE_URL ||
  "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  const authHeader = req.headers.get("authorization");
  if (!authHeader) {
    return NextResponse.json({ detail: "NO_TOKEN" }, { status: 401 });
  }

  const backendUrl = `${BACKEND_API_BASE_URL}/threads`;
  const res = await fetch(backendUrl, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      authorization: authHeader,
    },
  });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") || "application/json" },
  });
}

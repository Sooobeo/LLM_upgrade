// src/app/api/threads/route.ts
import { NextRequest, NextResponse } from "next/server";

const BACKEND_API_BASE_URL =
  process.env.BACKEND_API_BASE_URL || "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  try {
    // 브라우저에서 온 Authorization 그대로 읽기
    const authHeader = req.headers.get("authorization");

    console.log("[/api/threads] incoming Authorization from browser:", authHeader);

    const backendUrl = `${BACKEND_API_BASE_URL}/threads`;
    console.log("[/api/threads] proxy ->", backendUrl);

    const backendHeaders: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (authHeader) {
      // 백엔드로도 동일하게 전달
      backendHeaders["Authorization"] = authHeader;
    }

    const res = await fetch(backendUrl, {
      method: "GET",
      headers: backendHeaders,
    });

    const text = await res.text();
    let data: any = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }

    console.log(
      "[/api/threads] backend status:",
      res.status,
      "body:",
      data
    );

    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    console.error("[/api/threads] proxy error:", e);
    return NextResponse.json(
      { detail: "Proxy error in /api/threads", error: String(e) },
      { status: 500 },
    );
  }
}

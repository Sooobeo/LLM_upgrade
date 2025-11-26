"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type TokenParams = Record<string, string>;

function parseParams(input: string): TokenParams {
  const trimmed = input.startsWith("#") || input.startsWith("?") ? input.substring(1) : input;
  const params = new URLSearchParams(trimmed);
  const out: TokenParams = {};
  params.forEach((value, key) => {
    out[key] = value;
  });
  return out;
}

export default function AuthCallbackPage() {
  const router = useRouter();
  const [message, setMessage] = useState("스레드를 불러오는 중입니다...");

  useEffect(() => {
    const hashParams = parseParams(window.location.hash || "");
    const searchParams = parseParams(window.location.search || "");
    const allParams = { ...searchParams, ...hashParams };
    const refreshToken = allParams["refresh_token"];

    if (!refreshToken) {
      setMessage("로그인 정보가 없습니다. 다시 로그인해주세요.");
      const t = setTimeout(() => router.replace("/"), 1200);
      return () => clearTimeout(t);
    }

    const backend = process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL;
    fetch(`${backend}/auth/google/set-session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        const text = await res.text();
        const data = text ? JSON.parse(text) : null;
        if (!res.ok) {
          throw new Error(text || "세션 설정 실패");
        }
        // 백엔드가 돌려준 access_token을 로컬에도 저장해 threads 페이지의 토큰 검증을 통과시킴
        const accessToken = data?.access_token;
        const refreshFromResp = data?.refresh_token ?? refreshToken;
        if (accessToken) {
          // lazy import to avoid ssr issues
          const { auth } = await import("@/lib/auth");
          auth.setSession({ accessToken, refreshToken: refreshFromResp });
        }
        setMessage("로그인 완료! 스레드로 이동합니다...");
        setTimeout(() => router.replace("/threads"), 400);
      })
      .catch((err) => {
        setMessage(`세션 설정에 실패했습니다. 다시 로그인해주세요. (${err.message})`);
        setTimeout(() => router.replace("/"), 1400);
      });
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0c1424] text-white">
      <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-4 text-center shadow-lg backdrop-blur">
        <p className="text-sm text-blue-100">{message}</p>
      </div>
    </main>
  );
}

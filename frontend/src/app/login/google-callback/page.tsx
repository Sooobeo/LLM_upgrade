"use client";

import { useEffect, useState } from "react";
import { auth } from "@/lib/auth";

function parseTokens() {
  if (typeof window === "undefined") return {} as Record<string, string>;
  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const search = window.location.search.startsWith("?")
    ? window.location.search.slice(1)
    : window.location.search;

  const params = new URLSearchParams(hash || search);
  const result: Record<string, string> = {};
  params.forEach((v, k) => {
    result[k] = v;
  });
  return result;
}

export default function GoogleCallbackPage() {
  const [message, setMessage] = useState("구글 로그인 처리 중입니다...");

  useEffect(() => {
    const params = parseTokens();
    const error = params.error || params.error_description;
    if (error) {
      setMessage(`로그인에 실패했습니다: ${error}`);
      return;
    }

    const accessToken = params.access_token;
    const refreshToken = params.refresh_token;

    if (!accessToken) {
      setMessage("토큰을 받지 못했습니다. 다시 시도해주세요.");
      return;
    }

    auth.setSession({ accessToken, refreshToken });
    window.location.replace("/threads");
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center bg-zinc-50">
      <div className="rounded-xl border bg-white px-6 py-4 text-sm text-zinc-700 shadow-sm">
        {message}
      </div>
    </main>
  );
}

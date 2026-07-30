"use client";

import { useEffect, useRef, useState } from "react";
import { auth } from "@/lib/auth";
import { API_BASE_URL } from "@/lib/apiFetch";

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
  const callbackStarted = useRef(false);
  const [message, setMessage] = useState("구글 로그인 처리 중입니다...");

  useEffect(() => {
    if (callbackStarted.current) return;
    callbackStarted.current = true;

    const params = parseTokens();
    const error = params.error || params.error_description;
    if (error) {
      setMessage(`로그인에 실패했습니다: ${error}`);
      return;
    }

    const refreshToken = params.refresh_token;

    if (!refreshToken) {
      setMessage("토큰을 받지 못했습니다. 다시 시도해주세요.");
      return;
    }

    window.history.replaceState(null, "", window.location.pathname);
    fetch(`${API_BASE_URL}/auth/google/set-session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (response) => {
        const data = await response.json().catch(() => null);
        if (!response.ok || !data?.access_token) throw new Error("session");
        auth.setToken(data.access_token);
        window.location.replace("/threads");
      })
      .catch(() => setMessage("로그인 세션을 만들 수 없습니다. 다시 로그인해 주세요."));
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center bg-zinc-50">
      <div className="rounded-xl border bg-white px-6 py-4 text-sm text-zinc-700 shadow-sm">
        {message}
      </div>
    </main>
  );
}

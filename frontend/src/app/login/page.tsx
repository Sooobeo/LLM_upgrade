"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { auth } from "@/lib/auth";
import { API_BASE_URL } from "@/lib/apiFetch";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    }).then(async (response) => {
      const data = response.ok ? await response.json() : null;
      if (data?.access_token) {
        auth.setToken(data.access_token);
        router.replace("/threads");
      }
    });
  }, [router]);

  async function handleLogin(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login/password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok || !data?.access_token) {
        setError(data?.detail?.message || "이메일 또는 비밀번호를 확인해 주세요.");
        return;
      }
      auth.setToken(data.access_token);
      router.replace("/threads");
    } catch {
      setError("로그인 서버에 연결할 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/5 p-8 text-white shadow-2xl backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">
          llm upgrade: chat archiving
        </p>
        <h1 className="mt-2 text-2xl font-bold">대화 아카이브 로그인</h1>
        <p className="mt-1 text-sm text-blue-100">
          저장한 스레드와 브랜치를 불러오려면 로그인하세요.
        </p>
        <form className="mt-6 space-y-4" onSubmit={handleLogin}>
          <label className="block text-sm font-semibold text-blue-50">
            이메일
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="name@example.com"
            />
          </label>
          <label className="block text-sm font-semibold text-blue-50">
            비밀번호
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="••••••••"
            />
          </label>
          {error && <div className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? "아카이브를 여는 중..." : "로그인하고 아카이브 열기"}
          </button>
        </form>
      </div>
      <button onClick={() => router.push("/")} className="mt-4 text-xs text-blue-200/70 hover:text-white">
        ← 처음 화면으로
      </button>
    </div>
  );
}

// src/app/login/page.tsx
"use client";

import { useState } from "react";
import Link from "next/link";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/login/password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const contentType = res.headers.get("content-type") || "";
      const text = await res.text();

      let data: any = null;
      if (contentType.includes("application/json")) {
        data = text ? JSON.parse(text) : null;
      }

      if (!res.ok) {
        setError(data?.detail?.msg || data?.detail || "로그인 실패");
        return;
      }

      const accessToken = data.access_token;
      if (!accessToken) {
        setError("access_token이 응답에 없습니다.");
        return;
      }

      
      window.location.href = "/threads";
    } catch (err) {
      console.error("[login] error:", err);
      setError("네트워크 오류 (백엔드 주소/포트 확인)");
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleLogin() {
    if (!SUPABASE_URL) {
      setError("Supabase URL이 설정되어 있지 않습니다. (.env 확인)");
      return;
    }

    const redirectTo = `${window.location.origin}/login/google-callback`;
    const url = `${SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to=${encodeURIComponent(
      redirectTo
    )}`;
    window.location.href = url;
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-zinc-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 border bg-white p-6 rounded-2xl shadow-sm"
      >
        <h1 className="text-xl font-semibold">로그인</h1>

        <div className="space-y-1">
          <label className="block text-sm">Email</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            placeholder="계정 이메일을 입력하시오" // ✅ placeholder 변경
            required
          />
        </div>

        <div className="space-y-1">
          <label className="block text-sm">Password</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="비밀번호를 입력하시오"
            required
          />
        </div>

        {error && (
          <p className="text-sm text-red-500 whitespace-pre-wrap">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 rounded bg-black text-white text-sm disabled:opacity-60"
        >
          {loading ? "로그인 중..." : "로그인"}
        </button>

        <button
          type="button"
          onClick={handleGoogleLogin}
          className="w-full py-2 rounded border border-zinc-300 text-sm hover:bg-zinc-50"
        >
          구글 로그인
        </button>

        {/* ✅ 회원가입 링크 */}
        <p className="text-sm text-center text-zinc-600">
          계정이 없나요?{" "}
          <Link href="/signup" className="underline text-black font-medium">
            회원가입
          </Link>
        </p>
      </form>
    </main>
  );
}

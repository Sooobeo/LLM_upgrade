// src/app/login/page.tsx
"use client";

import { useState } from "react";
import { auth } from "@/lib/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("soob@gmail.com");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // ✅ 이제는 Next API 프록시 사용 (브라우저 → /api/..., CORS 걱정 X)
      const res = await fetch("/api/auth/login/password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        console.error("Login failed:", data);
        setError(data?.detail?.message || data?.detail || "로그인 실패");
        return;
      }

      const accessToken = data.access_token;
      if (!accessToken) {
        setError("access_token이 응답에 없습니다.");
        return;
      }

      // ✅ 통일된 auth 유틸 사용
      auth.setToken(accessToken);

      // ✅ /threads로 이동
      window.location.href = "/threads";
    } catch (err: any) {
      console.error(err);
      setError("네트워크 오류");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 border p-6 rounded-lg">
        <h1 className="text-xl font-semibold">로그인</h1>

        <div className="space-y-1">
          <label className="block text-sm">Email</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
          />
        </div>

        <div className="space-y-1">
          <label className="block text-sm">Password</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
          />
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 rounded bg-black text-white text-sm disabled:opacity-60"
        >
          {loading ? "로그인 중..." : "로그인"}
        </button>
      </form>
    </main>
  );
}

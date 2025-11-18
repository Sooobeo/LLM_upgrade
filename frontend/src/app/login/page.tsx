"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // 디버그용: 실제로 무엇을 보내는지 확인
      console.log("login with:", {
        email: email,
        password: password,
      });

      const res = await fetch("http://localhost:8000/auth/login/password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),    // 공백 방지
          password: password,
        }),
      });

      const text = await res.text();
      let data: any = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = null;
      }

      if (!res.ok) {
        const detailMsg =
          data?.detail?.msg ||
          data?.detail?.error ||
          data?.detail?.error_description ||
          data?.detail ||
          text ||
          `status ${res.status}`;

        throw new Error(detailMsg);
      }

      // Supabase password 로그인 응답 패턴들 커버
      const accessToken =
        data?.access_token ??
        data?.accessToken ??
        data?.session?.access_token;

      const userId =
        data?.user?.id ??
        data?.user_id ??
        email.trim();

      if (!accessToken) {
        throw new Error("access_token이 응답에 없습니다.");
      }

      auth.setToken(accessToken);
      auth.setUserId(userId);

      console.log("login success, token:", accessToken.slice(0, 12), "...");

      router.push("/threads");
    } catch (err: any) {
      console.error("login error:", err);
      setError(err.message ?? "로그인 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50">
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white px-8 py-10 shadow-sm">
        <h1 className="text-2xl font-semibold mb-6">GPT 로그 웹 로그인</h1>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-1">
            <label className="block text-sm font-medium text-zinc-700">
              이메일
            </label>
            <input
              type="email"
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="block text-sm font-medium text-zinc-700">
              비밀번호
            </label>
            <input
              type="password"
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <p className="text-sm text-red-500 whitespace-pre-wrap">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="mt-4 w-full rounded-lg bg-black px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
            disabled={loading}
          >
            {loading ? "로그인 중..." : "로그인"}
          </button>
        </form>
      </div>
    </div>
  );
}

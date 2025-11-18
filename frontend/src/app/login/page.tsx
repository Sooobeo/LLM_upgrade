/*
아이디, 비밀번호 입력
로그인 버튼 -> FastAPI /auth/login 요청
성공 여부랑 상관없이 (개발 단계에서는)
토큰/유저 정보를 저장하고 /threads로 이동
*/

"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const router = useRouter();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let data: any = null;

      try {
        const res = await fetch("http://localhost:8000/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        // 응답이 JSON이면 읽고, 아니면 그냥 무시
        try {
          data = await res.json();
        } catch {
          data = null;
        }

        console.log("login response:", res.status, data);
      } catch (networkError) {
        console.warn("네트워크 에러 (그래도 개발용으로 계속 진행):", networkError);
      }

      // 백엔드 응답에 access_token / user_id가 있으면 쓰고,
      // 없으면 임시(dev) 값으로 채워서 진행
      const token = data?.access_token ?? `dev-token-${email}`;
      const userId = data?.user_id ?? email;

      auth.setToken(token);
      auth.setUserId(userId);

      // 로그인 성공했다고 치고 /threads로 이동
      router.push("/threads");
    } catch (err) {
      console.error(err);
      setError("로그인 처리 중 오류가 발생했습니다.");
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
            <p className="text-sm text-red-500">
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

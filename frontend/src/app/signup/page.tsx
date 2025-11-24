"use client";

import { useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export default function SignupPage() {
  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setOk(false);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/signup/password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nickname, email, password }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        const msg =
          data?.detail?.msg ||
          data?.detail?.message ||
          data?.detail ||
          `회원가입 실패 (status ${res.status})`;
        throw new Error(msg);
      }

      setOk(true);
    } catch (err: any) {
      console.error("[signup] error:", err);
      setError(err.message ?? "회원가입 중 오류");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-zinc-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 border p-6 rounded-lg bg-white"
      >
        <h1 className="text-xl font-semibold">회원가입</h1>

        <div className="space-y-1">
          <label className="block text-sm">닉네임</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="닉네임을 입력하시오"
            required
          />
        </div>

        <div className="space-y-1">
          <label className="block text-sm">이메일</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="계정 이메일을 입력하시오"
            type="email"
            required
          />
        </div>

        <div className="space-y-1">
          <label className="block text-sm">비밀번호</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="비밀번호를 입력하시오"
            type="password"
            required
          />
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}
        {ok && (
          <p className="text-sm text-green-600">
            회원가입 성공! 이제 로그인 해줘.
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 rounded bg-black text-white text-sm disabled:opacity-60"
        >
          {loading ? "가입 중..." : "회원가입"}
        </button>
      </form>
    </main>
  );
}

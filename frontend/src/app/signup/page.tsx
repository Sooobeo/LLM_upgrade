"use client";

import Link from "next/link";
import { useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

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
      setError(err.message ?? "회원가입 오류");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] px-6 py-10 text-white">
      <div className="mx-auto flex min-h-[80vh] max-w-5xl flex-col gap-10 md:flex-row md:items-center md:justify-between">
        <div className="space-y-4 text-left md:max-w-lg">
          <p className="inline-flex items-center rounded-full bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-blue-200">
            Join LLM Workspace
          </p>
          <h1 className="text-4xl font-bold md:text-5xl">시작할 준비가 되셨나요?</h1>
          <p className="text-sm text-blue-100 md:text-base">
            계정을 만들어 대화 기록을 저장하고, 검색하고, 워크플로를 이어가세요. 구글 로그인과 비밀번호 로그인을 모두 지원합니다.
          </p>
          <div className="flex flex-wrap gap-3 text-xs text-blue-100">
            <span className="rounded-full border border-white/20 px-3 py-1">보안 인증</span>
            <span className="rounded-full border border-white/20 px-3 py-1">워크플로 최적화</span>
            <span className="rounded-full border border-white/20 px-3 py-1">실시간 동기화</span>
          </div>
          <Link href="/" className="text-xs font-semibold text-blue-100 underline underline-offset-4">
            랜딩으로 돌아가기
          </Link>
        </div>

        <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/5 p-8 shadow-2xl backdrop-blur">
          <div className="mb-6 space-y-2">
            <h2 className="text-2xl font-semibold text-white">회원가입</h2>
            <p className="text-sm text-blue-100">필수 정보를 입력해 계정을 만들어주세요.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className="block text-sm text-blue-100">닉네임</label>
              <input
                className="w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-sm text-white placeholder:text-blue-200 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-200/40"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="팀에서 보여질 이름"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm text-blue-100">이메일</label>
              <input
                className="w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-sm text-white placeholder:text-blue-200 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-200/40"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                type="email"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm text-blue-100">비밀번호</label>
              <input
                className="w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-sm text-white placeholder:text-blue-200 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-200/40"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="영문, 숫자 조합 권장"
                type="password"
                required
              />
            </div>

            {error && <p className="rounded-lg border border-red-300/40 bg-red-500/10 px-3 py-2 text-sm text-red-100">{error}</p>}
            {ok && <p className="rounded-lg border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">회원가입 완료! 로그인해주세요.</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-white px-4 py-3 text-sm font-semibold text-[#0c1424] shadow-lg shadow-blue-500/20 transition hover:-translate-y-0.5 hover:bg-blue-50 disabled:opacity-70"
            >
              {loading ? "가입 중..." : "회원가입"}
            </button>

            <p className="text-center text-xs text-blue-100">
              이미 계정이 있나요?{" "}
              <Link href="/" className="font-semibold text-white underline underline-offset-4">
                로그인으로 돌아가기
              </Link>
            </p>
          </form>
        </div>
      </div>
    </main>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

export default function LandingPage() {
  const [showLogin, setShowLogin] = useState(false);
  const router = useRouter();

  const handleGoogleLogin = useCallback(() => {
    const redirectTo = `${window.location.origin}/auth/callback`;
    const base = process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL;
    const url = `${base}/auth/google/login?redirect_to=${encodeURIComponent(redirectTo)}`;
    window.location.href = url;
  }, []);

  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white">
      {/* Landing slide */}
      <div
        className={`absolute inset-0 flex items-center justify-center px-6 transition-transform duration-700 ease-in-out ${
          showLogin ? "-translate-y-full" : "translate-y-0"
        }`}
      >
        <div className="max-w-4xl text-center space-y-6">
          <p className="inline-flex items-center rounded-full bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-blue-200">
            LLM Workspace
          </p>
          <h1 className="text-5xl font-bold md:text-6xl">LLM upgrade, 더욱 편리하게</h1>
          <p className="text-lg text-blue-100 md:text-xl">
            대화 기록을 한곳에 정리하고 더 빠르게 업무를 시작하세요. 직관적인 워크스페이스와 검색으로 생산성을 높여
            드립니다.
          </p>
          <div className="flex items-center justify-center gap-3 text-sm text-blue-100">
            <span className="rounded-full border border-white/20 px-3 py-1">빠른 검색</span>
            <span className="rounded-full border border-white/20 px-3 py-1">보안 인증</span>
            <span className="rounded-full border border-white/20 px-3 py-1">워크플로 최적화</span>
          </div>
        </div>

        <button
          aria-label="시작하기"
          onClick={() => setShowLogin(true)}
          className="absolute bottom-10 inline-flex h-14 w-14 items-center justify-center rounded-full bg-white text-[#0d1b33] shadow-xl ring-2 ring-white/40 transition hover:translate-y-1 hover:bg-blue-50"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="h-6 w-6 animate-bounce"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 9.75 12 17.25 19.5 9.75" />
          </svg>
        </button>
      </div>

      {/* Login slide */}
      <div
        className={`absolute inset-0 flex items-center justify-center px-6 transition-transform duration-700 ease-in-out ${
          showLogin ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="relative w-full max-w-5xl overflow-hidden rounded-3xl border border-white/15 bg-white/5 backdrop-blur-xl">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-cyan-400/10" />
          <div className="relative grid gap-0 md:grid-cols-2">
            <div className="flex flex-col justify-center space-y-6 px-8 py-10 md:px-12 md:py-14">
              <p className="text-sm font-semibold uppercase tracking-[0.25em] text-blue-100">로그인</p>
              <h2 className="text-3xl font-bold md:text-4xl">시작할 준비가 되셨나요?</h2>
              <p className="text-sm leading-6 text-blue-100">
                이메일과 비밀번호로 로그인하거나, 간편하게 구글 계정으로 바로 시작하세요. 안전하게 접근하고 워크플로를
                이어가세요.
              </p>
              <div className="flex flex-wrap gap-3 text-xs text-blue-100">
                <span className="rounded-full border border-white/20 px-3 py-1">SSO 지원</span>
                <span className="rounded-full border border-white/20 px-3 py-1">구글 연동</span>
                <span className="rounded-full border border-white/20 px-3 py-1">개인 데이터 보호</span>
              </div>
            </div>

            <div className="relative bg-white text-slate-900 md:rounded-l-3xl md:rounded-r-none">
              <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-400" />
              <div className="flex flex-col gap-6 px-8 py-10 md:px-10 md:py-14">
                <div className="space-y-1">
                  <h3 className="text-2xl font-semibold">LLM Upgrade 계정</h3>
                  <p className="text-sm text-slate-600">로그인을 이어가거나 새로 시작하세요.</p>
                </div>

                <button
                  onClick={handleGoogleLogin}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  <svg className="h-5 w-5" viewBox="0 0 533.5 544.3" xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M533.5 278.4c0-17.4-1.5-34.2-4.3-50.4H272v95.3h146.9c-6.3 33.9-25 62.6-53.5 81.8v68.2h86.7c50.8-46.8 80.4-115.8 80.4-194.9z"
                      fill="#4285f4"
                    />
                    <path
                      d="M272 544.3c72.6 0 133.6-24 178.2-65.2l-86.7-68.2c-24.1 16.2-55 25.7-91.5 25.7-70.4 0-130.1-47.5-151.5-111.4H31.4v69.9C75.3 487.7 167.2 544.3 272 544.3z"
                      fill="#34a853"
                    />
                    <path
                      d="M120.5 325.2c-5.6-16.6-8.8-34.2-8.8-52.3s3.2-35.7 8.8-52.3V150.7H31.4C11.3 190.1 0 233.4 0 278c0 44.6 11.3 87.9 31.4 127.3l89.1-70.1z"
                      fill="#fbbc05"
                    />
                    <path
                      d="M272 107.3c39.5 0 75 13.6 103 40.3l77.1-77.1C405.6 24.1 344.6 0 272 0 167.2 0 75.3 56.6 31.4 150.7l89.1 69.9C141.9 154.8 201.6 107.3 272 107.3z"
                      fill="#ea4335"
                    />
                  </svg>
                  구글 계정으로 계속하기
                </button>

                <div className="space-y-3">
                  <label className="text-sm font-medium text-slate-700">이메일</label>
                  <input
                    type="email"
                    placeholder="name@example.com"
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-sm font-medium text-slate-700">비밀번호</label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  />
                </div>

                <div className="flex flex-col gap-3">
                  <button
                    onClick={() => router.push("/login")}
                    className="w-full rounded-xl bg-[#0d1b33] px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:-translate-y-0.5 hover:bg-[#0f223e]"
                  >
                    로그인하기
                  </button>
                  <Link
                    href="/signup"
                    className="w-full text-center text-sm font-semibold text-blue-700 underline underline-offset-4"
                  >
                    아직 계정이 없나요? 가입하기
                  </Link>
                </div>
              </div>
              <button
                aria-label="메인으로 돌아가기"
                onClick={() => setShowLogin(false)}
                className="absolute left-4 top-4 inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:scale-105"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="h-5 w-5"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

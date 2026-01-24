"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { auth } from "@/lib/auth";
import { supabase } from "@/lib/supabaseClient";

export default function LandingPage() {
  const router = useRouter();
  const [hasSession, setHasSession] = useState<boolean>(false);
  const [showLogin, setShowLogin] = useState(false);
  const containerRef = useRef<HTMLElement | null>(null);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (!supabase) {
      const token = auth.getToken();
      setHasSession(!!token);
      return;
    }

    supabase.auth.getSession().then(({ data }) => {
      const token = data.session?.access_token || auth.getToken();
      setHasSession(!!token);
    });
  }, []);

  const handleGoogleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/threads`,
      },
    });
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      if (isAnimating) return;

      // 아래로 스크롤 → Login
      if (e.deltaY > 50 && !showLogin) {
        setIsAnimating(true);
        setShowLogin(true);
        setTimeout(() => setIsAnimating(false), 700);
      }

      // 위로 스크롤 → Landing
      if (e.deltaY < -50 && showLogin) {
        setIsAnimating(true);
        setShowLogin(false);
        setTimeout(() => setIsAnimating(false), 700);
      }
    };

    el.addEventListener("wheel", onWheel, { passive: true });

    return () => {
      el.removeEventListener("wheel", onWheel);
    };
  }, [showLogin, isAnimating]);


  return (
      <main
        ref={containerRef}
        className="relative min-h-screen overflow-hidden bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white"
      >      
      {/* ===== Landing Slide ===== */}
      <div
        className={`absolute inset-0 flex items-center justify-center px-6 transition-transform duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] ${
          showLogin ? "-translate-y-full" : "translate-y-0"
        }`}
      >
        <div className="max-w-4xl text-center space-y-8">
          <span className="inline-flex rounded-full border border-white/20 bg-white/5 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-blue-200 backdrop-blur">
            LLM Upgrade
          </span>

          <h1 className="text-5xl font-extrabold leading-tight md:text-6xl">
            대화 기록을 정리하고
            <br />
            <span className="bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
              바로 시작하세요
            </span>
          </h1>

          <p className="mx-auto max-w-2xl text-lg text-blue-100">
            대화 기록을 한곳에 정리하고 빠르게 이어서 작업하세요.
            직관적인 워크스페이스와 검색으로 생산성을 높입니다.
          </p>

          <div className="flex justify-center gap-3 text-sm text-blue-100">
            <span className="rounded-full border border-white/20 px-3 py-1">빠른 검색</span>
            <span className="rounded-full border border-white/20 px-3 py-1">보안 인증</span>
            <span className="rounded-full border border-white/20 px-3 py-1">워크플로 최적화</span>
          </div>
        </div>

        <button
          aria-label="시작하기"
          onClick={() => setShowLogin(true)}
          className="absolute bottom-10 inline-flex h-14 w-14 items-center justify-center rounded-full border border-white/30 bg-white/5 text-white backdrop-blur transition hover:-translate-y-1 hover:bg-white/10"
          >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            className="h-6 w-6 animate-bounce"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 9.75 12 17.25 19.5 9.75" />
          </svg>
        </button>
      </div>

      {/* ===== Login Slide ===== */}
      <div
        className={`absolute inset-0 flex items-center justify-center px-6 transition-transform duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] ${
          showLogin ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="relative w-full max-w-5xl overflow-hidden rounded-3xl border border-white/15 bg-white/5 backdrop-blur-xl">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-cyan-400/10" />

          <div className="relative grid md:grid-cols-2">
            {/* Left */}
            <div className="flex flex-col justify-center space-y-6 px-8 py-10 md:px-12 md:py-14">
              <p className="text-sm font-semibold uppercase tracking-[0.25em] text-blue-100">
                로그인
              </p>
              <h2 className="text-3xl font-bold md:text-4xl">
                시작할 준비가 되셨나요?
              </h2>
              <p className="text-sm leading-6 text-blue-100">
                구글 계정 또는 이메일로 안전하게 로그인하고
                바로 스레드 작업을 시작하세요.
              </p>

              <div className="flex flex-wrap gap-3 text-xs text-blue-100">
                <span className="rounded-full border border-white/20 px-3 py-1">SSO 지원</span>
                <span className="rounded-full border border-white/20 px-3 py-1">구글 연동</span>
                <span className="rounded-full border border-white/20 px-3 py-1">데이터 보호</span>
              </div>
            </div>

            {/* Right */}
            <div className="relative bg-white text-slate-900 md:rounded-l-3xl">
              <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-400" />

              <div className="flex flex-col gap-6 px-8 py-10 md:px-10 md:py-14">
                <div>
                  <br/>
                  <h3 className="text-2xl font-semibold">LLM Upgrade 계정</h3>
                  <p className="text-sm text-slate-600">
                    로그인하거나 새로 시작하세요.
                  </p>
                </div>

                <div className="block mt-2 mb-5 flex flex-col gap-3">
                  <button
                    onClick={handleGoogleLogin}
                    className="flex w-full items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold shadow transition hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <svg
                      className="h-5 w-5"
                      viewBox="0 0 533.5 544.3"
                      xmlns="http://www.w3.org/2000/svg"
                    >
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

                    <span>구글 계정으로 계속하기</span>
                  </button>

                  <button
                    onClick={() => router.push("/login")}
                    className="rounded-xl bg-[#0d1b33] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#0f223e]"
                  >
                    이메일로 로그인
                  </button>

                  {hasSession && (
                    <button
                      onClick={() => router.push("/threads")}
                      className="rounded-xl border border-blue-300 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-700"
                    >
                      스레드로 이동 →
                    </button>
                  )}
                </div>

              </div>

              <button
                aria-label="메인으로 돌아가기"
                onClick={() => setShowLogin(false)}
                className="absolute left-4 top-4 inline-flex h-9 w-9 items-center justify-center rounded-full border bg-white text-slate-700 shadow transition hover:scale-105"
              >
                ＜
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

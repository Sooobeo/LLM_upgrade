"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";

import { getOAuthCallbackUrl } from "@/lib/oauthRedirect";
import { SUPABASE_PROJECT_URL } from "@/lib/supabaseClient";

export default function LandingPage() {
  const router = useRouter();
  const [showLogin, setShowLogin] = useState(false);
  const containerRef = useRef<HTMLElement | null>(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const [googleLoginLoading, setGoogleLoginLoading] = useState(false);
  const [googleLoginError, setGoogleLoginError] = useState<string | null>(null);
  const [oauthRedirecting, setOauthRedirecting] = useState(false);

  const handleGoogleLogin = () => {
    setGoogleLoginLoading(true);
    setGoogleLoginError(null);
    try {
      const authorizeUrl = new URL(
        "/auth/v1/authorize",
        SUPABASE_PROJECT_URL,
      );
      authorizeUrl.searchParams.set("provider", "google");
      authorizeUrl.searchParams.set(
        "redirect_to",
        getOAuthCallbackUrl(),
      );
      window.location.assign(authorizeUrl.toString());
    } catch {
      setGoogleLoginLoading(false);
      setGoogleLoginError("Google 로그인 주소를 만들지 못했습니다.");
    }
  };

  useEffect(() => {
    const hashParams = new URLSearchParams(
      window.location.hash.startsWith("#")
        ? window.location.hash.slice(1)
        : window.location.hash,
    );
    const searchParams = new URLSearchParams(window.location.search);
    const isOAuthReturn = [
      "access_token",
      "refresh_token",
      "error",
      "error_code",
      "error_description",
    ].some((key) => hashParams.has(key) || searchParams.has(key));

    if (!isOAuthReturn) return;

    setOauthRedirecting(true);
    const callbackUrl = new URL("/auth/callback", window.location.origin);
    callbackUrl.search = window.location.search;
    callbackUrl.hash = window.location.hash;
    window.location.replace(callbackUrl.toString());
  }, []);

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

  if (oauthRedirecting) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0c1424] text-white">
        <div
          role="status"
          className="rounded-2xl border border-white/10 bg-white/5 px-6 py-5 text-center shadow-lg backdrop-blur"
        >
          <span
            aria-hidden="true"
            className="mx-auto mb-3 block h-6 w-6 animate-spin rounded-full border-2 border-blue-200/30 border-t-cyan-300"
          />
          <p className="text-sm text-blue-100">
            Google 로그인을 완료하는 중입니다...
          </p>
        </div>
      </main>
    );
  }

  return (
    <main
        ref={containerRef}
        className="relative h-[100dvh] min-h-[36rem] overflow-hidden bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white"
      >
      {/* ===== Landing Slide ===== */}
      <div
        className={`absolute inset-0 flex items-center justify-center overflow-y-auto px-4 py-10 transition-transform duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] sm:px-6 ${
          showLogin ? "-translate-y-full" : "translate-y-0"
        }`}
      >
        <div className="max-w-4xl space-y-5 pb-16 text-center sm:space-y-8 sm:pb-0">
          <span className="inline-flex rounded-full border border-white/20 bg-white/5 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-blue-200 backdrop-blur">
            Conversation archive
          </span>

          <h1 className="bg-gradient-to-r from-blue-300 via-white to-cyan-300 bg-clip-text pb-2 text-3xl font-extrabold leading-[1.2] text-transparent sm:text-4xl md:text-6xl md:leading-[1.16]">
            llm upgrade: chat archiving
          </h1>

          <p className="mx-auto max-w-2xl text-base leading-7 text-blue-100 sm:text-lg">
            흩어진 LLM 대화를 스레드로 보관하고, Gemini 브랜치를
            시각화해 생각의 흐름까지 한곳에 아카이빙하세요.
          </p>

          <div className="flex flex-wrap justify-center gap-2 text-xs text-blue-100 sm:gap-3 sm:text-sm">
            <span className="rounded-full border border-white/20 px-3 py-1">대화 아카이빙</span>
            <span className="rounded-full border border-white/20 px-3 py-1">브랜치 맵</span>
            <span className="rounded-full border border-white/20 px-3 py-1">안전한 접근</span>
          </div>
        </div>

        <button
          aria-label="시작하기"
          onClick={() => setShowLogin(true)}
          className="absolute bottom-[max(1.25rem,env(safe-area-inset-bottom))] inline-flex h-12 w-12 items-center justify-center rounded-full border border-white/30 bg-white/5 text-white backdrop-blur transition hover:bg-white/10 sm:bottom-10 sm:h-14 sm:w-14"
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
        className={`absolute inset-0 flex items-center justify-center overflow-y-auto overscroll-contain px-3 py-4 transition-transform duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] sm:px-6 ${
          showLogin ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="relative my-auto w-full max-w-5xl overflow-hidden rounded-2xl border border-white/15 bg-white/5 backdrop-blur-xl sm:rounded-3xl">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-cyan-400/10" />

          <div className="relative grid md:grid-cols-2">
            {/* Left */}
            <div className="hidden flex-col justify-center space-y-6 px-8 py-10 md:flex md:px-12 md:py-14">
              <p className="text-sm font-semibold uppercase tracking-[0.25em] text-blue-100">
                Archive access
              </p>
              <h2 className="text-3xl font-bold md:text-4xl">
                저장한 대화로 돌아오세요
              </h2>
              <p className="text-sm leading-6 text-blue-100">
                로그인하면 보관한 스레드, 브랜치 폴더와 코멘트를
                안전하게 불러와 바로 이어갈 수 있습니다.
              </p>

              <div className="flex flex-wrap gap-3 text-xs text-blue-100">
                <span className="rounded-full border border-white/20 px-3 py-1">스레드 보관</span>
                <span className="rounded-full border border-white/20 px-3 py-1">Google 로그인</span>
                <span className="rounded-full border border-white/20 px-3 py-1">계정별 보호</span>
              </div>
            </div>

            {/* Right */}
            <div className="relative rounded-2xl bg-white text-slate-900 md:rounded-l-3xl md:rounded-r-none">
              <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-400" />

              <div className="flex flex-col gap-5 px-5 pb-[max(2rem,env(safe-area-inset-bottom))] pt-16 sm:px-8 sm:py-10 md:px-10 md:py-14">
                <div>
                  <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-blue-600 md:hidden">
                    llm upgrade: chat archiving
                  </p>
                  <h3 className="text-xl font-semibold sm:text-2xl">Chat Archiving 계정</h3>
                  <p className="text-sm text-slate-600">
                    대화 아카이브에 안전하게 접속하세요.
                  </p>
                </div>

                <div className="mt-2 flex flex-col gap-3 sm:mb-5">
                  <button
                    onClick={handleGoogleLogin}
                    disabled={googleLoginLoading}
                    aria-busy={googleLoginLoading}
                    className="flex min-h-12 w-full items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm font-semibold shadow transition hover:shadow-md disabled:cursor-wait disabled:opacity-70 sm:px-4"
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

                    {googleLoginLoading ? (
                      <>
                        <span
                          aria-hidden="true"
                          className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600"
                        />
                        <span>Google 로그인으로 이동 중...</span>
                      </>
                    ) : (
                      <span>Google 계정으로 아카이브 열기</span>
                    )}
                  </button>

                  {googleLoginError && (
                    <p
                      role="alert"
                      className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
                    >
                      {googleLoginError}
                    </p>
                  )}

                  <button
                    onClick={() => router.push("/threads")}
                    className="min-h-12 rounded-xl bg-[#0d1b33] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#0f223e]"
                  >
                    이메일 계정으로 아카이브 열기
                  </button>

                </div>

              </div>

              <button
                aria-label="메인으로 돌아가기"
                onClick={() => setShowLogin(false)}
                className="absolute left-4 top-4 inline-flex h-11 w-11 items-center justify-center rounded-full border bg-white text-slate-700 shadow transition hover:scale-105"
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

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { auth } from "@/lib/auth";
import { supabase } from "@/lib/supabaseClient";

export default function LandingPage() {
  const router = useRouter();
  const [hasSession, setHasSession] = useState<boolean>(false);

  useEffect(() => {
    // Check existing session but do not redirect; just toggle CTA
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

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 text-white">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-10 px-6 py-16 text-center">
        <p className="rounded-full border border-white/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-blue-100">
          LLM Upgrade
        </p>
        <div className="space-y-4">
          <h1 className="text-4xl font-bold md:text-5xl">대화 기록을 정리하고 바로 시작하세요</h1>
          <p className="text-sm text-blue-100 md:text-base">
            소개 페이지 → 로그인 버튼(구글/일반) → 로그인 후 스레드 목록으로 이동합니다.
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-3">
          <button
            onClick={handleGoogleLogin}
            className="flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-900 shadow hover:-translate-y-0.5 hover:shadow-md transition"
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
            구글 로그인
          </button>

          <button
            onClick={() => router.push("/login")}
            className="rounded-xl border border-white/30 bg-white/10 px-4 py-3 text-sm font-semibold text-white shadow-inner hover:-translate-y-0.5 hover:bg-white/15 transition"
          >
            일반 로그인
          </button>

          {hasSession && (
            <button
              onClick={() => router.push("/threads")}
              className="rounded-xl border border-blue-200 bg-blue-500/20 px-4 py-3 text-sm font-semibold text-blue-50 shadow-inner hover:-translate-y-0.5 hover:bg-blue-500/30 transition"
            >
              스레드로 이동
            </button>
          )}
        </div>

        <div className="mt-8 grid w-full gap-4 rounded-3xl border border-white/10 bg-white/5 p-6 text-left backdrop-blur md:grid-cols-3">
          <div>
            <p className="text-sm font-semibold text-white">정리된 스레드</p>
            <p className="text-xs text-blue-100">대화 흐름을 한눈에 보고 다시 이어서 질문하세요.</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">빠른 로그인</p>
            <p className="text-xs text-blue-100">구글/일반 로그인 후 바로 스레드 목록으로 이동합니다.</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">보안</p>
            <p className="text-xs text-blue-100">토큰이 없을 땐 데이터 로드 없이 안전하게 안내만 합니다.</p>
          </div>
        </div>
      </div>
    </main>
  );
}

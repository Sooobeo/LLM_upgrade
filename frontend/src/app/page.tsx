// src/app/page.tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";

// Backend base URL for Google OAuth (FastAPI)
const BACKEND_BASE =
  process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL || "http://127.0.0.1:8000";

/**
 * Public landing page.
 * - If already authenticated, redirect to /threads.
 * - Otherwise, show Google login button that calls FastAPI OAuth flow.
 */
export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const token = auth.getToken();
    if (token) {
      router.replace("/threads");
    }
  }, [router]);

  const handleGoogleLogin = () => {
    window.location.href = `${BACKEND_BASE}/auth/google/login`;
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-zinc-50 px-4">
      <div className="max-w-md w-full space-y-6 text-center">
        <h1 className="text-2xl font-semibold">Welcome to LLM Upgrade</h1>
        <p className="text-sm text-zinc-600">
          로그인 후 대화 기록을 확인하세요. 계정이 없으면 회원가입을 진행해 주세요.
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={handleGoogleLogin}
            className="px-4 py-2 rounded bg-black text-white text-sm"
          >
            구글 로그인
          </button>
          <a
            href="/signup"
            className="px-4 py-2 rounded border border-zinc-300 text-sm hover:bg-zinc-100"
          >
            회원가입
          </a>
        </div>
      </div>
    </main>
  );
}

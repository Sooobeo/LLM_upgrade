// src/app/page.tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";

/**
 * Public landing page.
 * - Does NOT call protected APIs on mount (prevents 401 before login)
 * - Redirects to /threads if already logged in
 */
export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const token = auth.getToken();
    if (token) {
      router.replace("/threads");
    }
  }, [router]);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-zinc-50 px-4">
      <div className="max-w-md w-full space-y-6 text-center">
        <h1 className="text-2xl font-semibold">Welcome to LLM Upgrade</h1>
        <p className="text-sm text-zinc-600">
          로그인 후 대화 기록을 확인하세요. 아직 계정이 없다면 회원가입을 진행해주세요.
        </p>
        <div className="flex items-center justify-center gap-3">
          <a
            href="/login"
            className="px-4 py-2 rounded bg-black text-white text-sm"
          >
            로그인
          </a>
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

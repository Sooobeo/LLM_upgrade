"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// 로그인 페이지를 별도로 쓰지 않고 바로 스레드 화면으로 리다이렉트
export default function LoginRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/threads");
  }, [router]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-zinc-50 text-zinc-700">
      <div className="rounded-xl border bg-white px-6 py-4 text-sm shadow-sm">
        스레드 화면으로 이동합니다...
      </div>
    </main>
  );
}

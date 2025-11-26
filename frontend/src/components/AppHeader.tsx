"use client";

import { useRouter } from "next/navigation";

import { useCurrentUser } from "@/hooks/useCurrentUser";

export function AppHeader() {
  const router = useRouter();
  const { displayName, loading, error } = useCurrentUser({ redirectIfMissing: true });

  const goToMyPage = () => {
    router.push("/mypage");
  };

  return (
    <header className="fixed top-0 z-20 w-full border-b border-white/10 bg-slate-900/70 text-white shadow-lg backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4 md:px-6">
        <div
          className="cursor-pointer text-sm font-semibold tracking-wide text-blue-100"
          onClick={() => router.push("/threads")}
        >
          LLM Upgrade
        </div>
        <div className="flex items-center gap-3">
          {loading ? (
            <span className="text-xs text-blue-100">사용자 확인 중…</span>
          ) : error ? (
            <button
              className="rounded-full border border-red-300/40 bg-red-500/20 px-3 py-1 text-xs font-semibold text-red-50 shadow-sm hover:bg-red-500/30"
              onClick={() => router.push("/")}
            >
              다시 로그인
            </button>
          ) : (
            <button
              onClick={goToMyPage}
              className="rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-white/20"
            >
              안녕하세요, {displayName || "사용자"}님
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

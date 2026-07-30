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
    <header className="fixed inset-x-0 top-0 z-20 w-full border-b border-white/10 bg-slate-900/85 pt-[env(safe-area-inset-top)] text-white shadow-lg backdrop-blur">
      <div className="mx-auto flex h-14 min-w-0 max-w-5xl items-center justify-between gap-3 px-3 sm:px-4 md:px-6">
        <div
          className="min-w-0 cursor-pointer truncate text-xs font-semibold tracking-wide text-blue-100 sm:text-sm"
          onClick={() => router.push("/threads")}
        >
          llm upgrade: chat archiving
        </div>
        <div className="flex min-w-0 shrink-0 items-center gap-2 sm:gap-3">
          {loading ? (
            <span className="text-xs text-blue-100">사용자 확인 중…</span>
          ) : error ? (
            <button
              className="rounded-full border border-red-300/40 bg-red-500/20 px-3 py-1 text-xs font-semibold text-red-50 shadow-sm hover:bg-red-500/30"
              onClick={() => router.replace("/login")}
            >
              다시 로그인
            </button>
          ) : (
            <button
              onClick={goToMyPage}
              className="max-w-36 truncate rounded-full border border-white/20 bg-white/10 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-white/20 sm:max-w-64 sm:px-4 sm:text-sm"
            >
              <span className="hidden sm:inline">안녕하세요, </span>
              {displayName || "사용자"}
              <span className="hidden sm:inline">님</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

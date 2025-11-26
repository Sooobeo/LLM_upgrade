"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";

type Thread = {
  id: string;
  title?: string | null;
  created_at?: string | null;
};

export default function ThreadsPage() {
  const router = useRouter();

  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = auth.getToken();
    if (!token) {
      console.log("[ThreadsPage] no token, redirect /");
      router.push("/");
      return;
    }

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await api("/threads", { method: "GET" });
        const list: Thread[] = Array.isArray(data) ? data : data?.threads ?? [];
        setThreads(list);
      } catch (err: any) {
        console.error("threads load error:", err);
        setError(err.message ?? String(err));
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white">
        <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-4 text-center shadow-lg backdrop-blur">
          <p className="text-sm text-blue-100">스레드를 불러오는 중입니다...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white">
        <div className="max-w-md rounded-2xl border border-white/15 bg-white/5 px-6 py-5 text-sm text-red-100 shadow-lg backdrop-blur">
          <div className="font-semibold mb-1 text-red-200">스레드를 불러오지 못했어요.</div>
          <div className="text-xs text-red-100 break-all">{error}</div>
          <button
            className="mt-4 rounded-lg border border-red-300/50 px-4 py-2 text-xs text-red-50 hover:bg-red-50/10"
            onClick={() => window.location.reload()}
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] px-6 py-10 text-white">
      <div className="mx-auto max-w-5xl">
        <header className="mb-10 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <p className="inline-flex items-center rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-200">
              LLM Threads
            </p>
            <div>
              <h1 className="text-3xl font-bold md:text-4xl">나의 대화 스레드</h1>
              <p className="mt-2 text-sm text-blue-100">
                최근 대화를 모아보고, 이어서 작업하거나 새로운 스레드를 시작하세요.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              className="rounded-xl border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-white/15"
              onClick={() => router.push("/threads/new")}
            >
              새 스레드
            </button>
            <button
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-xs text-blue-100 transition hover:bg-white/10"
              onClick={() => {
                auth.clear();
                router.push("/");
              }}
            >
              로그아웃
            </button>
          </div>
        </header>

        {threads.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-10 text-center text-sm text-blue-100 shadow-lg backdrop-blur">
            <p className="font-semibold text-white">아직 저장된 스레드가 없습니다.</p>
            <p className="mt-2 text-xs text-blue-200">새 스레드를 만들어 대화를 시작해 보세요.</p>
            <button
              className="mt-4 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs font-semibold text-white hover:bg-white/15"
              onClick={() => router.push("/threads/new")}
            >
              새 스레드 만들기
            </button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {threads.map((t) => (
              <div
                key={t.id}
                className="group cursor-pointer rounded-2xl border border-white/10 bg-white/5 p-5 shadow-md backdrop-blur transition hover:-translate-y-1 hover:bg-white/10"
                onClick={() => router.push(`/threads/${t.id}`)}
              >
                <div className="flex items-start justify-between">
                  <h3 className="text-lg font-semibold text-white">
                    {t.title || "제목 없음"}
                  </h3>
                  <span className="text-[11px] text-blue-200 opacity-80 group-hover:opacity-100">
                    {t.created_at ? new Date(t.created_at).toLocaleDateString() : ""}
                  </span>
                </div>
                <p className="mt-2 text-xs text-blue-100">이어 보기 ›</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

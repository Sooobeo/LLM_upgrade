// src/app/threads/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
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
      console.log("[ThreadsPage] no token, redirect /login");
      router.push("/login");
      return;
    }

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const data = await apiFetch("/threads", { method: "GET" });

        const list: Thread[] = Array.isArray(data)
          ? data
          : data?.threads ?? [];

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
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <p className="text-sm text-zinc-600">스레드를 불러오는 중입니다...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <div className="max-w-md rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <div className="font-semibold mb-1">
            스레드를 불러오지 못했습니다.
          </div>
          <div className="text-xs text-red-500 break-all">
            {error}
          </div>
          <button
            className="mt-3 rounded-md border border-red-300 px-3 py-1 text-xs"
            onClick={() => window.location.reload()}
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 p-8">
      <div className="mx-auto max-w-3xl">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">나의 GPT 대화 스레드</h1>
          <button
            className="text-xs text-zinc-500 underline"
            onClick={() => {
              auth.clear();
              router.push("/login");
            }}
          >
            로그아웃
          </button>
        </header>

        {threads.length === 0 ? (
          <p className="text-sm text-zinc-600">
            아직 저장된 스레드가 없어요.
          </p>
        ) : (
          <ul className="space-y-3">
            {threads.map((t) => (
              <li
                key={t.id}
                className="cursor-pointer rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm hover:bg-zinc-50"
                onClick={() => router.push(`/threads/${t.id}`)}
              >
                <div className="font-medium">
                  {t.title || "(제목 없음)"}
                </div>
                {t.created_at && (
                  <div className="mt-1 text-xs text-zinc-500">
                    {new Date(t.created_at).toLocaleString()}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// src/app/threads/page.tsx
"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type ThreadSummary = {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
  last_message_preview?: string | null;
};

export default function ThreadsPage() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch("/threads");
        // 백엔드 response_model=ThreadsListResp { threads: [...] } 라고 가정
        setThreads(data.threads ?? []);
      } catch (err: any) {
        console.error(err);
        setError(err.message || "목록 불러오기 실패");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  if (loading) return <p className="p-4">불러오는 중...</p>;
  if (error) return <p className="p-4 text-red-500">{error}</p>;

  return (
    <main className="max-w-2xl mx-auto p-4 space-y-4">
      <h1 className="text-xl font-semibold mb-2">내 스레드</h1>

      <a
        href="/threads/new"
        className="inline-block text-sm px-3 py-1 border rounded hover:bg-gray-50"
      >
        + 새 스레드 만들기
      </a>

      <ul className="space-y-2">
        {threads.map((t) => (
          <li key={t.id} className="border rounded px-3 py-2 hover:bg-gray-50">
            <a href={`/threads/${t.id}`} className="block">
              <div className="flex justify-between items-center">
                <span className="font-medium text-sm">{t.title}</span>
                <span className="text-xs text-gray-500">
                  {t.message_count} messages
                </span>
              </div>
              {t.last_message_preview && (
                <p className="text-xs text-gray-600 mt-1 truncate">
                  {t.last_message_preview}
                </p>
              )}
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}

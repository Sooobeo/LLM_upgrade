/*
메시지 리스트
GPT와의 대화 기록 보여주기
검색창 추가 가능
*/

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";

type ThreadDetail = {
  id: string;
  title?: string | null;
  created_at?: string;
  // 필요하면 더 추가
};

type Message = {
  id: string;
  role: string;
  content: string;
  created_at?: string;
};

export default function ThreadDetailPage() {
  const params = useParams<{ threadId: string }>();
  const router = useRouter();
  const threadId = params.threadId;

  const [thread, setThread] = useState<ThreadDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = auth.getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    async function load() {
      try {
        setError(null);

        // 1) 스레드 정보
        const t = await api(`/threads/${threadId}`, { method: "GET" });
        setThread(t);

        // 2) 메시지 목록
        const m = await api(
          `/threads/${threadId}/messages?limit=50&offset=0&order=asc`,
          { method: "GET" }
        );

        const list = Array.isArray(m) ? m : m.messages ?? [];
        setMessages(list);
      } catch (err: any) {
        console.error("thread detail error:", err);
        setError(err.message ?? String(err));
      } finally {
        setLoading(false);
      }
    }

    if (threadId) {
      load();
    }
  }, [router, threadId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-zinc-600">
        대화 불러오는 중...
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 max-w-md">
          <div className="font-semibold mb-1">스레드를 불러오지 못했습니다.</div>
          <div className="text-xs text-red-500 break-all">{error}</div>
        </div>
      </div>
    );
  }

  if (!thread) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-zinc-600">
        스레드를 찾을 수 없습니다.
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 p-6">
      <div className="mx-auto max-w-3xl space-y-4">
        <button
          className="text-xs text-zinc-500 underline"
          onClick={() => router.push("/threads")}
        >
          ← 스레드 목록으로
        </button>

        <header>
          <h1 className="text-xl font-semibold">
            {thread.title || "(제목 없음)"}
          </h1>
          {thread.created_at && (
            <p className="mt-1 text-xs text-zinc-500">
              {new Date(thread.created_at).toLocaleString()}
            </p>
          )}
        </header>

        <section className="mt-4 space-y-3">
          {messages.length === 0 ? (
            <p className="text-sm text-zinc-500">아직 메시지가 없습니다.</p>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`rounded-lg border px-3 py-2 text-sm ${
                  m.role === "assistant"
                    ? "bg-zinc-900 text-zinc-50 border-zinc-900"
                    : "bg-white border-zinc-200"
                }`}
              >
                <div className="text-[10px] uppercase tracking-wide text-zinc-400 mb-1">
                  {m.role}
                </div>
                <div className="whitespace-pre-wrap">{m.content}</div>
              </div>
            ))
          )}
        </section>
      </div>
    </div>
  );
}

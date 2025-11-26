"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppLayout } from "@/components/AppLayout";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";

export default function NewThreadPage() {
  const router = useRouter();
  const { loading: userLoading } = useCurrentUser({ redirectIfMissing: true });

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = auth.getToken();
    if (!token) {
      router.push("/");
    }
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setError(null);

    try {
      const token = auth.getToken();
      if (!token) {
        setError("로그인이 필요합니다.");
        router.push("/");
        return;
      }

      const body = {
        title: title || "제목 없는 스레드",
        messages: [
          {
            role: "user",
            // Keep a single space if empty to satisfy server-side validation.
            content: content || " ",
          },
        ],
      };

      const data = await api("/threads", {
        method: "POST",
        body: JSON.stringify(body),
      });

      const threadId = data?.thread_id;
      if (threadId) {
        router.push(`/threads/${threadId}`);
      }
    } catch (err: any) {
        setError(err?.message || "스레드 생성에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-4xl px-6 py-10 text-white">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <p className="inline-flex items-center rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-200">
              New Thread
            </p>
            <div>
              <h1 className="text-3xl font-bold md:text-4xl">새 스레드 만들기</h1>
              <p className="mt-2 text-sm text-blue-100">
                제목과 첫 메시지를 입력해서 대화를 시작해보세요.
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => router.push("/threads")}
              className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-white/20"
            >
              ← 스레드 목록으로
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-lg backdrop-blur">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-semibold text-blue-100">제목</label>
              <input
                className="w-full rounded-xl border border-white/15 bg-slate-900/40 px-4 py-3 text-sm text-white shadow-inner focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-300/40"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="스레드 제목을 입력하세요"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-blue-100">첫 메시지</label>
              <textarea
                className="w-full rounded-xl border border-white/15 bg-slate-900/40 px-4 py-3 text-sm text-white shadow-inner focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-300/40 min-h-[160px]"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="GPT에게 보낼 첫 메시지를 적어보세요."
              />
            </div>

            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-50">
                {error}
              </div>
            )}

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => router.push("/threads")}
                className="rounded-xl border border-white/20 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={loading || userLoading}
                className="rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 transition hover:-translate-y-0.5 hover:bg-blue-500 disabled:opacity-60"
              >
                {loading ? "생성 중..." : "스레드 생성"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}

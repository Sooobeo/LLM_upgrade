// src/app/threads/new/page.tsx
"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";

export default function NewThreadPage() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState(""); // 첫 user 메시지
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const body = {
        title: title || "제목 없는 스레드",
        messages: [
          {
            role: "user",
            content: content || " ",
          },
        ],
      };

      const data = await apiFetch("/threads", {
        method: "POST",
        body: JSON.stringify(body),
      });

      // data: { thread_id, status: "saved" }
      const threadId = data.thread_id;
      if (threadId) {
        window.location.href = `/threads/${threadId}`;
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "스레드 생성 실패");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-4">
      <h1 className="text-xl font-semibold mb-3">새 스레드 만들기</h1>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-sm mb-1">제목</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="스레드 제목을 입력하세요"
          />
        </div>

        <div>
          <label className="block text-sm mb-1">첫 메시지</label>
          <textarea
            className="w-full border rounded px-3 py-2 text-sm min-h-[120px]"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="GPT에게 보낼 첫 메시지를 적어보세요"
          />
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-black text-white text-sm rounded disabled:opacity-60"
        >
          {loading ? "생성 중..." : "스레드 생성"}
        </button>
      </form>
    </main>
  );
}

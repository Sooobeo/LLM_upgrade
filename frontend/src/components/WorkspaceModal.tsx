"use client";

import { useState } from "react";

type Props = {
  threadId: string;
  onClose: () => void;
  onSuccess?: (data: any) => void;
};

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL;

export function WorkspaceModal({ threadId, onClose, onSuccess }: Props) {
  const [emailInput, setEmailInput] = useState("");
  const [emails, setEmails] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const addEmail = () => {
    const next = emailInput.trim();
    if (!next) return;
    if (emails.includes(next)) return;
    setEmails((prev) => [...prev, next]);
    setEmailInput("");
  };

  const handleSubmit = async (e?: React.FormEvent<HTMLFormElement> | React.MouseEvent<HTMLButtonElement>) => {
    e?.preventDefault();
    console.log("[workspace] handleSubmit called");
    console.log("[workspace] emails:", emails);

    if (emails.length === 0) {
      setError("최소 한 명 이상의 이메일을 추가해주세요.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setInfo(null);

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      console.log("[workspace] token:", token);
      if (!token) {
        setError("로그인이 필요합니다.");
        return;
      }

      console.log("[workspace] about to fetch");
      const res = await fetch(`${API_BASE}/threads/${threadId}/workspace`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ emails }),
      });
      console.log("[workspace] after fetch", res.status);
      const data = await res.json().catch(() => null);
      console.log("[workspace] response body", data);
      if (!res.ok) {
        setError(data?.detail || "워크스페이스 생성 중 오류가 발생했습니다.");
        return;
      }

      setInfo("워크스페이스가 생성되었습니다.");
      const threadIdFromResp = (data && (data.thread_id || data.id)) || threadId;
      onSuccess?.({ threadId: threadIdFromResp, data });
      console.log("[workspace] onSuccess called with threadId:", threadIdFromResp);
      onClose();
    } catch (err: any) {
      console.error("[workspace] fetch error", err);
      setError(err?.message || "네트워크 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/15 bg-slate-900 p-6 text-white shadow-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">워크스페이스로 전환하기</h3>
            <button type="button" onClick={onClose} className="text-sm text-blue-100 hover:text-white">
              닫기
            </button>
          </div>

          <p className="text-sm text-blue-100">이 스레드를 함께 사용할 멤버 이메일을 추가하세요.</p>

          <div className="flex gap-2">
            <input
              type="email"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              placeholder="user@example.com"
              className="flex-1 rounded-xl border border-white/15 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-400 focus:outline-none"
            />
            <button
              type="button"
              onClick={addEmail}
              className="rounded-xl bg-white/10 px-3 py-2 text-sm font-semibold text-white hover:bg-white/20"
            >
              추가
            </button>
          </div>

          {emails.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {emails.map((em) => (
                <span key={em} className="rounded-full bg-white/10 px-3 py-1 text-xs text-white">
                  {em}
                </span>
              ))}
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-100">
              {error}
            </div>
          )}
          {info && (
            <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
              {info}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-white/15 px-4 py-2 text-sm text-white hover:bg-white/10"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 hover:bg-blue-500 disabled:opacity-60"
            >
              {submitting ? "처리 중..." : "워크스페이스 만들기"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

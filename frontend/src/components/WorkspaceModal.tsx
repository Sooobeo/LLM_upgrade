"use client";

import { useState } from "react";
import { createWorkspace } from "@/lib/threadApi";

type Props = {
  threadId: string;
  onClose: () => void;
  onSuccess?: (threadId: string) => void;
};

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

  const handleSubmit = async (
    e?: React.FormEvent<HTMLFormElement> | React.MouseEvent<HTMLButtonElement>,
  ) => {
    e?.preventDefault();

    if (emails.length === 0) {
      setError("최소 한 명 이상의 이메일을 추가해주세요.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setInfo(null);

    try {
      const data = await createWorkspace(threadId, emails);

      setInfo("워크스페이스가 생성되었습니다.");

      const threadIdFromResp = data?.thread_id || data?.id || threadId;
      onSuccess?.(threadIdFromResp);

      setTimeout(() => {
        onClose();
      }, 800);
    } catch (workspaceError) {
      setError(
        workspaceError instanceof Error
          ? workspaceError.message
          : "워크스페이스 생성 중 오류가 발생했습니다.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto overscroll-contain bg-black/50 p-3 pb-[max(.75rem,env(safe-area-inset-bottom))] pt-[max(.75rem,env(safe-area-inset-top))]">
      <div className="my-auto max-h-[calc(100dvh-1.5rem)] w-full max-w-md overflow-y-auto rounded-2xl border border-white/15 bg-slate-900 p-4 text-white shadow-2xl sm:p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">워크스페이스로 전환하기</h3>
            <button type="button" onClick={onClose} className="min-h-10 px-2 text-sm text-blue-100 hover:text-white">
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
              className="min-h-12 min-w-0 flex-1 rounded-xl border border-white/15 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-400 focus:outline-none"
            />
            <button
              type="button"
              onClick={addEmail}
              className="min-h-12 rounded-xl bg-white/10 px-3 py-2 text-sm font-semibold text-white hover:bg-white/20"
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
              className="min-h-11 rounded-xl border border-white/15 px-4 py-2 text-sm text-white hover:bg-white/10"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="min-h-11 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 hover:bg-blue-500 disabled:opacity-60"
            >
              {submitting ? "처리 중..." : "워크스페이스 만들기"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

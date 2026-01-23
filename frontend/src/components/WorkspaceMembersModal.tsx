"use client";

import { useEffect, useState } from "react";

import { fetchMembers, createWorkspace } from "@/lib/threadApi";

type Member = {
  user_id?: string;
  email?: string;
  role?: string;
  created_at?: string;
};

type Props = {
  threadId: string;
  onClose: () => void;
};

function parseEmails(raw: string): string[] {
  return Array.from(
    new Set(
      raw
        .split(/[\s,]+/)
        .map((v) => v.trim())
        .filter(Boolean),
    ),
  );
}

export function WorkspaceMembersModal({ threadId, onClose }: Props) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [emailInput, setEmailInput] = useState("");
  const [adding, setAdding] = useState(false);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const data = await fetchMembers(threadId);
        setMembers(data);
      } catch (e: any) {
        setError(e?.message || "멤버를 불러오지 못했습니다.");
      } finally {
        setLoading(false);
      }
    })();
  }, [threadId]);

  const handleAdd = async () => {
    const emails = parseEmails(emailInput);
    if (!emails.length) {
      setInfo("이메일을 입력하세요.");
      return;
    }
    try {
      setAdding(true);
      setError(null);
      setInfo(null);
      const res = await createWorkspace(threadId, emails);
      setInfo(
        `추가 완료. added_members: ${(res.added_members || []).join(", ")}, not_found: ${(res.not_found || []).join(
          ", ",
        )}`,
      );
      const data = await fetchMembers(threadId);
      setMembers(data);
      setEmailInput("");
    } catch (e: any) {
      setError(e?.message || "멤버 추가 실패");
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-slate-900 p-6 text-white shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">Workspace 멤버</h3>
          <button onClick={onClose} className="text-sm text-blue-100 hover:text-white">
            닫기
          </button>
        </div>

        {loading ? (
          <div className="text-sm text-blue-100">불러오는 중...</div>
        ) : error ? (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-100">{error}</div>
        ) : (
          <div className="space-y-3">
            {members.length === 0 ? (
              <p className="text-sm text-blue-100">멤버가 없습니다.</p>
            ) : (
              <div className="space-y-2">
                {members.map((m, idx) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                    <div>
                      <div className="text-sm font-semibold">{m.email || m.user_id}</div>
                      <div className="text-xs text-blue-100">{m.role} · {m.created_at ? new Date(m.created_at).toLocaleString() : ""}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="mt-4 space-y-2">
          <label className="text-sm font-semibold text-blue-100">멤버 추가</label>
          <textarea
            value={emailInput}
            onChange={(e) => setEmailInput(e.target.value)}
            placeholder="user1@example.com, user2@example.com"
            className="w-full rounded-xl border border-white/15 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-400 focus:outline-none"
          />
          <button
            onClick={handleAdd}
            disabled={adding}
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-blue-500 disabled:opacity-60"
          >
            {adding ? "추가 중..." : "추가"}
          </button>
          {info && <div className="text-xs text-green-200">{info}</div>}
          {error && <div className="text-xs text-red-200">{error}</div>}
        </div>
      </div>
    </div>
  );
}

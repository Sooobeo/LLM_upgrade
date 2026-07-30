"use client";

import { useEffect, useState } from "react";

import { createWorkspace, fetchMembers } from "@/lib/threadApi";

type Member = {
  user_id?: string;
  email?: string;
  role?: string;
  created_at?: string;
};

type Props = {
  threadId: string;
  onClose: () => void;
  canManage?: boolean;
};

function parseEmails(raw: string): string[] {
  return Array.from(
    new Set(
      raw
        .split(/[\s,]+/)
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  );
}

export function WorkspaceMembersModal({
  threadId,
  onClose,
  canManage = false,
}: Props) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [emailInput, setEmailInput] = useState("");
  const [adding, setAdding] = useState(false);
  const [info, setInfo] = useState<string | null>(null);

  const loadMembers = async () => {
    setLoading(true);
    setError(null);
    try {
      setMembers(await fetchMembers(threadId));
    } catch (memberError) {
      setError(
        memberError instanceof Error
          ? memberError.message
          : "멤버를 불러오지 못했습니다.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadMembers();
    // threadId identifies the modal's complete data scope.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  const handleAdd = async () => {
    if (!canManage) return;
    const emails = parseEmails(emailInput);
    if (!emails.length) {
      setInfo("추가할 이메일을 입력해 주세요.");
      return;
    }

    setAdding(true);
    setError(null);
    setInfo(null);
    try {
      const result = await createWorkspace(threadId, emails);
      const added = result.added_members || [];
      const notFound = result.not_found || [];
      setInfo(
        notFound.length
          ? `${added.length}명 추가 완료 · 찾을 수 없는 계정: ${notFound.join(", ")}`
          : `${added.length}명의 멤버를 반영했습니다.`,
      );
      setEmailInput("");
      await loadMembers();
    } catch (memberError) {
      setError(
        memberError instanceof Error ? memberError.message : "멤버 추가에 실패했습니다.",
      );
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-slate-900 p-6 text-white shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">워크스페이스 멤버</h3>
            <p className="mt-1 text-xs text-blue-100/65">
              이 멤버들은 루트 스레드의 전체 브랜치 트리를 볼 수 있습니다.
            </p>
          </div>
          <button onClick={onClose} className="text-sm text-blue-100 hover:text-white">
            닫기
          </button>
        </div>

        {loading ? (
          <div className="text-sm text-blue-100">멤버를 불러오는 중...</div>
        ) : error ? (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-100">
            {error}
          </div>
        ) : members.length === 0 ? (
          <p className="text-sm text-blue-100">등록된 멤버가 없습니다.</p>
        ) : (
          <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
            {members.map((member) => (
              <div
                key={`${member.user_id}-${member.role}`}
                className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2"
              >
                <div>
                  <div className="text-sm font-semibold">
                    {member.email || member.user_id}
                  </div>
                  <div className="text-xs text-blue-100">
                    {member.role || "member"}
                    {member.created_at
                      ? ` · ${new Date(member.created_at).toLocaleString()}`
                      : ""}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {canManage ? (
          <div className="mt-4 space-y-2">
            <label className="text-sm font-semibold text-blue-100">멤버 추가</label>
            <textarea
              value={emailInput}
              onChange={(event) => setEmailInput(event.target.value)}
              placeholder="user@example.com"
              className="w-full rounded-xl border border-white/15 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-400 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => void handleAdd()}
              disabled={adding}
              className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-blue-500 disabled:opacity-60"
            >
              {adding ? "추가 중..." : "추가"}
            </button>
            {info && <div className="text-xs text-green-200">{info}</div>}
            {error && <div className="text-xs text-red-200">{error}</div>}
          </div>
        ) : (
          <p className="mt-4 rounded-xl border border-indigo-300/15 bg-indigo-300/5 px-3 py-2 text-xs text-indigo-100/75">
            멤버 추가는 워크스페이스 소유자만 할 수 있습니다.
          </p>
        )}
      </div>
    </div>
  );
}

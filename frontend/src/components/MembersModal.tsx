"use client";

import { useEffect, useState } from "react";

type Member = {
  user_id: string;
  email?: string | null;
  role?: string | null;
  created_at?: string | null;
};

type Props = {
  threadId: string;
  onClose: () => void;
};

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL;

export function MembersModal({ threadId, onClose }: Props) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMembers = async () => {
      setError(null);
      setLoading(true);
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
        if (!token) {
          setError("로그인이 필요합니다.");
          return;
        }
        const res = await fetch(`${API_BASE}/threads/${threadId}/members`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json().catch(() => null);
        if (!res.ok) {
          setError(data?.detail || "멤버 목록을 불러올 수 없습니다.");
          return;
        }
        setMembers(Array.isArray(data) ? data : []);
      } catch (err: any) {
        setError(err?.message || "네트워크 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    };

    fetchMembers();
  }, [threadId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/15 bg-slate-900 p-6 text-white shadow-2xl">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">멤버 보기</h3>
          <button type="button" onClick={onClose} className="text-sm text-blue-100 hover:text-white">
            닫기
          </button>
        </div>

        {loading ? (
          <div className="mt-4 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-blue-100">
            불러오는 중...
          </div>
        ) : error ? (
          <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        ) : members.length === 0 ? (
          <div className="mt-4 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-blue-100">
            멤버가 없습니다.
          </div>
        ) : (
          <div className="mt-4 space-y-2">
            {members.map((m) => (
              <div
                key={m.user_id}
                className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{m.email || m.user_id}</span>
                  <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-[11px] font-semibold text-blue-100">
                    {m.role || "member"}
                  </span>
                </div>
                {m.created_at && (
                  <div className="mt-1 text-[11px] text-blue-200">
                    추가됨: {new Date(m.created_at).toLocaleString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

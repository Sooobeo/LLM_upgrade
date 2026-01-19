"use client";

import { ThreadSummary } from "@/lib/threadApi";

type Props = {
  threads: ThreadSummary[];
  isLoading?: boolean;
  onSelect: (threadId: string) => void;
  onNew: () => void;
};

export function ThreadList({ threads, isLoading, onSelect, onNew }: Props) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-600 shadow-sm">
        불러오는 중...
      </div>
    );
  }

  if (!threads.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-8 text-center shadow-sm">
        <p className="text-sm text-slate-600">아직 스레드가 없습니다.</p>
        <button
          className="mt-3 rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          onClick={onNew}
        >
          새 스레드 만들기
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Recent threads</h2>
        <button
          className="rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          onClick={onNew}
        >
          New Thread
        </button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {threads.map((t) => (
          <button
            key={t.id}
            onClick={() => onSelect(t.id)}
            className="group flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="text-base font-semibold text-slate-900 line-clamp-1">
                  {t.title || "Untitled"}
                </h3>
                {t.last_message_preview && (
                  <p className="mt-1 text-xs text-slate-600 line-clamp-2">{t.last_message_preview}</p>
                )}
              </div>
              {t.is_workspace && (
                <span className="rounded-full bg-blue-50 px-2 py-1 text-[11px] font-semibold text-blue-700">
                  Workspace
                </span>
              )}
            </div>
            <div className="mt-auto flex items-center gap-3 pt-3 text-[11px] text-slate-500">
              <span>{t.message_count ?? 0} msgs</span>
              <span>·</span>
              <span>{t.created_at ? new Date(t.created_at).toLocaleString() : ""}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

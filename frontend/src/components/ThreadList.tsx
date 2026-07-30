"use client";

import {
  BriefcaseBusiness,
  Check,
  MessageSquare,
  Pencil,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";

import { ThreadSummary } from "@/lib/threadApi";
import { DeleteConfirmModal } from "./DeleteConfirmModal";

type Props = {
  threads: ThreadSummary[];
  isLoading?: boolean;
  onSelect: (threadId: string) => void;
  onDelete?: (threadId: string) => void | Promise<void>;
  onRename?: (threadId: string, title: string) => void | Promise<void>;
  onWorkspace?: (thread: ThreadSummary) => void;
};

export function ThreadList({
  threads,
  isLoading,
  onSelect,
  onDelete,
  onRename,
  onWorkspace,
}: Props) {
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [loadingWorkspaceId, setLoadingWorkspaceId] = useState<string | null>(
    null,
  );
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [renamingThreadId, setRenamingThreadId] = useState<string | null>(null);
  const [renameError, setRenameError] = useState<string | null>(null);

  const startRename = (thread: ThreadSummary) => {
    setEditingThreadId(thread.id);
    setEditingTitle(thread.title || "");
    setRenameError(null);
  };

  const cancelRename = () => {
    if (renamingThreadId) return;
    setEditingThreadId(null);
    setEditingTitle("");
    setRenameError(null);
  };

  const commitRename = async (threadId: string) => {
    const title = editingTitle.trim();
    if (!title) {
      setRenameError("스레드 이름을 입력하세요.");
      return;
    }
    setRenamingThreadId(threadId);
    setRenameError(null);
    try {
      await onRename?.(threadId, title);
      setEditingThreadId(null);
      setEditingTitle("");
    } catch (error) {
      setRenameError(
        error instanceof Error ? error.message : "이름을 수정하지 못했습니다.",
      );
    } finally {
      setRenamingThreadId(null);
    }
  };

  const heading = (
    <div className="flex items-center gap-2">
      <MessageSquare size={18} className="text-cyan-200" />
      <h2 className="text-lg font-semibold text-white/90">Recent threads</h2>
      <span className="rounded-full bg-cyan-300/10 px-2 py-0.5 text-xs font-semibold text-cyan-100">
        {threads.length}
      </span>
    </div>
  );

  if (isLoading) {
    return (
      <section className="space-y-3">
        {heading}
        <div className="rounded-2xl border border-white/10 bg-slate-950/35 px-4 py-6 text-sm text-blue-100 shadow-sm">
          불러오는 중...
        </div>
      </section>
    );
  }

  if (!threads.length) {
    return (
      <section className="space-y-3">
        {heading}
        <div
          aria-label="일반 스레드 없음"
          className="min-h-24 rounded-2xl border border-dashed border-white/10 bg-slate-950/20"
        />
      </section>
    );
  }

  return (
    <>
      <section className="space-y-3">
        {heading}

        <div className="grid gap-3 sm:grid-cols-2">
          {threads.map((thread) => {
            const isEditing = editingThreadId === thread.id;
            const isRenaming = renamingThreadId === thread.id;
            return (
              <article
                key={thread.id}
                className="flex min-h-40 flex-col rounded-2xl border border-white/10 bg-slate-950/35 p-3 shadow-lg transition hover:border-cyan-300/35 hover:bg-slate-950/50 sm:p-4 sm:hover:-translate-y-0.5"
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
                      thread.is_workspace
                        ? "bg-indigo-300/15 text-indigo-200"
                        : "bg-cyan-300/10 text-cyan-200"
                    }`}
                  >
                    {thread.is_workspace ? (
                      <BriefcaseBusiness size={18} />
                    ) : (
                      <MessageSquare size={17} />
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    {isEditing ? (
                      <div>
                        <div className="flex items-center gap-1">
                          <input
                            autoFocus
                            value={editingTitle}
                            maxLength={200}
                            disabled={isRenaming}
                            onChange={(event) =>
                              setEditingTitle(event.target.value)
                            }
                            onKeyDown={(event) => {
                              if (event.key === "Enter") {
                                event.preventDefault();
                                void commitRename(thread.id);
                              } else if (event.key === "Escape") {
                                cancelRename();
                              }
                            }}
                            aria-label="스레드 이름"
                            className="min-w-0 flex-1 rounded-lg border border-cyan-300/30 bg-white/5 px-2 py-1 text-sm font-semibold text-white outline-none focus:ring-2 focus:ring-cyan-300/40"
                          />
                          <button
                            type="button"
                            onClick={() => void commitRename(thread.id)}
                            disabled={isRenaming}
                            aria-label="이름 저장"
                            className="flex h-9 w-9 items-center justify-center rounded-md text-emerald-300 hover:bg-emerald-300/10 disabled:opacity-50"
                          >
                            {isRenaming ? (
                              <span className="block h-4 w-4 animate-spin rounded-full border-2 border-emerald-300 border-t-transparent" />
                            ) : (
                              <Check size={16} />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={cancelRename}
                            disabled={isRenaming}
                            aria-label="이름 수정 취소"
                            className="flex h-9 w-9 items-center justify-center rounded-md text-white/45 hover:bg-white/10 disabled:opacity-50"
                          >
                            <X size={16} />
                          </button>
                        </div>
                        {renameError && (
                          <p className="mt-1 text-xs font-medium text-red-300">
                            {renameError}
                          </p>
                        )}
                      </div>
                    ) : (
                      <>
                        <h3 className="line-clamp-2 text-sm font-semibold leading-5 text-white">
                          {thread.title || "Untitled"}
                        </h3>
                        {thread.is_workspace && (
                          <span className="mt-1.5 inline-flex rounded-full border border-indigo-300/25 bg-indigo-300/10 px-2 py-0.5 text-[10px] font-bold text-indigo-100">
                            워크스페이스
                          </span>
                        )}
                      </>
                    )}
                  </div>

                  {!isEditing && onRename && (
                    <button
                      type="button"
                      onClick={() => startRename(thread)}
                      aria-label={`${thread.title || "Untitled"} 이름 수정`}
                      title="스레드 이름 수정"
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white/40 transition hover:bg-cyan-300/10 hover:text-cyan-200"
                    >
                      <Pencil size={15} />
                    </button>
                  )}
                </div>

                <div className="mt-3 truncate text-[10px] text-white/45">
                  {thread.created_at
                    ? new Date(thread.created_at).toLocaleString()
                    : ""}
                </div>

                <div className="mt-auto pt-3">
                  {(onWorkspace || onDelete) && (
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      {onWorkspace &&
                        (thread.is_workspace ||
                          thread.can_manage_workspace) && (
                        <button
                          type="button"
                          disabled={loadingWorkspaceId === thread.id}
                          onClick={async () => {
                            setLoadingWorkspaceId(thread.id);
                            try {
                              await onWorkspace(thread);
                            } finally {
                              setLoadingWorkspaceId(null);
                            }
                          }}
                          className="inline-flex min-h-10 min-w-36 flex-1 items-center justify-center gap-1.5 rounded-lg border border-indigo-300/15 bg-indigo-300/5 px-2 py-2 text-[11px] font-semibold text-indigo-100/75 transition hover:bg-indigo-300/10 disabled:opacity-50"
                        >
                          {loadingWorkspaceId === thread.id ? (
                            <span className="h-3 w-3 animate-spin rounded-full border-2 border-indigo-200 border-t-transparent" />
                          ) : (
                            <Users size={12} />
                          )}
                          {thread.is_workspace
                            ? "멤버 관리"
                            : "워크스페이스로 전환"}
                        </button>
                      )}
                      {onDelete && (
                        <button
                          type="button"
                          onClick={() => setDeleteTargetId(thread.id)}
                          className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-red-300/15 bg-red-300/5 px-3 py-2 text-[11px] font-semibold text-red-200/75 transition hover:bg-red-300/10"
                        >
                          <Trash2 size={12} />
                          삭제
                        </button>
                      )}
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => onSelect(thread.id)}
                    className="min-h-11 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-bold text-white/85 transition hover:border-cyan-300/30 hover:bg-cyan-300/10 hover:text-white"
                  >
                    스레드 열기
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <DeleteConfirmModal
        isOpen={Boolean(deleteTargetId)}
        onCancel={() => setDeleteTargetId(null)}
        onConfirm={async () => {
          if (deleteTargetId) {
            await onDelete?.(deleteTargetId);
          }
          setDeleteTargetId(null);
        }}
      />
    </>
  );
}

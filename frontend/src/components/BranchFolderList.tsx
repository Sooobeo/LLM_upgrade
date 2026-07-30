"use client";

import {
  Check,
  Folder,
  FolderOpen,
  GitBranch,
  HelpCircle,
  Pencil,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";

import { BranchNode, flattenBranchTree } from "@/lib/threadApi";
import { DeleteConfirmModal } from "./DeleteConfirmModal";

type Props = {
  roots: BranchNode[];
  onOpen: (rootId: string) => void;
  onRename?: (rootId: string, title: string) => void | Promise<void>;
  onDelete?: (rootId: string) => void | Promise<void>;
  onWorkspace?: (root: BranchNode) => void | Promise<void>;
};

export function BranchFolderList({
  roots,
  onOpen,
  onRename,
  onDelete,
  onWorkspace,
}: Props) {
  const [helpOpen, setHelpOpen] = useState(false);
  const [editingRootId, setEditingRootId] = useState<string | null>(null);
  const [titleDraft, setTitleDraft] = useState("");
  const [busyRootId, setBusyRootId] = useState<string | null>(null);
  const [deleteRootId, setDeleteRootId] = useState<string | null>(null);
  const [renameError, setRenameError] = useState<string | null>(null);

  if (!roots.length) return null;

  const saveTitle = async (rootId: string) => {
    const title = titleDraft.trim();
    if (!title) {
      setRenameError("폴더명을 입력하세요.");
      return;
    }
    setBusyRootId(rootId);
    setRenameError(null);
    try {
      await onRename?.(rootId, title);
      setEditingRootId(null);
      setTitleDraft("");
    } catch (error) {
      setRenameError(
        error instanceof Error ? error.message : "폴더명을 수정하지 못했습니다.",
      );
    } finally {
      setBusyRootId(null);
    }
  };

  return (
    <section className="mb-7 space-y-3">
      <div className="flex items-center gap-2">
        <Folder size={18} className="text-amber-300" />
        <h2 className="text-lg font-semibold text-white/90">브랜치 폴더</h2>
        <span className="rounded-full bg-amber-300/15 px-2 py-0.5 text-xs font-semibold text-amber-100">
          {roots.length}
        </span>
        <div className="relative">
          <button
            type="button"
            onClick={() => setHelpOpen((current) => !current)}
            aria-label="브랜치 폴더 도움말"
            aria-expanded={helpOpen}
            className="flex h-5 w-5 items-center justify-center rounded-full border border-amber-200/25 bg-amber-200/10 text-amber-100/70 transition hover:bg-amber-200/20 hover:text-amber-50"
          >
            <HelpCircle size={13} />
          </button>
          {helpOpen && (
            <div
              role="status"
              className="absolute left-7 top-0 z-40 w-56 rounded-xl border border-amber-200/25 bg-slate-950/95 px-3 pb-3 pt-8 text-xs text-amber-50 shadow-2xl backdrop-blur"
            >
              <button
                type="button"
                onClick={() => setHelpOpen(false)}
                aria-label="도움말 닫기"
                className="absolute right-2 top-2 rounded p-1 text-white/50 transition hover:bg-white/10 hover:text-white"
              >
                <X size={13} />
              </button>
              브랜치를 만들면 폴더가 생성됩니다.
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {roots.map((root) => {
          const nodes = flattenBranchTree(root);
          return (
            <article
              key={root.id}
              className="group relative mt-2 overflow-visible rounded-2xl border border-amber-300/30 bg-gradient-to-br from-amber-300/15 via-orange-300/10 to-slate-950/35 p-4 shadow-lg shadow-amber-950/15 transition hover:-translate-y-0.5 hover:border-amber-200/60 hover:shadow-xl"
            >
              <span
                aria-hidden="true"
                className="absolute -top-2 left-4 h-3 w-20 rounded-t-lg border-x border-t border-amber-300/35 bg-amber-300/20"
              />
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-amber-200/25 bg-amber-300/15 text-amber-200 shadow-inner">
                  <FolderOpen size={22} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-amber-200/70">
                    브랜치 폴더
                  </p>
                  {editingRootId === root.id ? (
                    <div className="mt-1">
                      <div className="flex items-center gap-1">
                        <input
                          autoFocus
                          value={titleDraft}
                          maxLength={200}
                          disabled={busyRootId === root.id}
                          onChange={(event) => setTitleDraft(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              event.preventDefault();
                              void saveTitle(root.id);
                            } else if (event.key === "Escape") {
                              setEditingRootId(null);
                              setRenameError(null);
                            }
                          }}
                          aria-label="폴더명"
                          className="min-w-0 flex-1 rounded-lg border border-amber-200/30 bg-black/20 px-2 py-1 text-sm font-bold text-white outline-none focus:ring-2 focus:ring-amber-200/30"
                        />
                        <button
                          type="button"
                          onClick={() => void saveTitle(root.id)}
                          disabled={busyRootId === root.id}
                          aria-label="폴더명 저장"
                          className="rounded p-1 text-emerald-300 hover:bg-emerald-300/10 disabled:opacity-40"
                        >
                          {busyRootId === root.id ? (
                            <span className="block h-3.5 w-3.5 animate-spin rounded-full border-2 border-emerald-300 border-t-transparent" />
                          ) : (
                            <Check size={14} />
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingRootId(null);
                            setRenameError(null);
                          }}
                          disabled={busyRootId === root.id}
                          aria-label="폴더명 수정 취소"
                          className="rounded p-1 text-white/45 hover:bg-white/10 disabled:opacity-40"
                        >
                          <X size={14} />
                        </button>
                      </div>
                      {renameError && (
                        <p className="mt-1 text-[10px] text-rose-300">
                          {renameError}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="mt-0.5 flex min-w-0 items-center gap-1.5">
                      <h3 className="min-w-0 flex-1 truncate text-base font-bold text-white">
                        {root.title || "제목 없는 스레드"}
                      </h3>
                      {root.can_manage && onRename && (
                        <button
                          type="button"
                          onClick={() => {
                            setEditingRootId(root.id);
                            setTitleDraft(root.title || "");
                            setRenameError(null);
                          }}
                          aria-label="폴더명 수정"
                          className="shrink-0 rounded p-1 text-white/40 transition hover:bg-amber-200/10 hover:text-amber-100"
                        >
                          <Pencil size={13} />
                        </button>
                      )}
                    </div>
                  )}
                  <div className="mt-2 flex items-center gap-2 text-xs text-amber-50/70">
                    <GitBranch size={13} />
                    <span>스레드 {nodes.length}개</span>
                    <span>·</span>
                    <span>루트 포함</span>
                  </div>
                  {root.is_workspace && (
                    <span className="mt-2 inline-flex rounded-full border border-indigo-300/25 bg-indigo-300/10 px-2 py-0.5 text-[10px] font-bold text-indigo-100">
                      워크스페이스
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  onClick={() => onOpen(root.id)}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-amber-200/25 bg-amber-200/15 px-4 py-2 text-sm font-bold text-amber-50 transition hover:bg-amber-200/25"
                >
                  <FolderOpen size={16} />
                  열기
                </button>
                {onWorkspace &&
                  (root.is_workspace || root.can_manage_workspace) && (
                    <button
                      type="button"
                      onClick={() => void onWorkspace(root)}
                      className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-indigo-300/25 bg-indigo-300/10 px-3 py-2 text-xs font-bold text-indigo-100 transition hover:bg-indigo-300/20"
                    >
                      <Users size={14} />
                      {root.is_workspace ? "멤버 관리" : "워크스페이스로 전환"}
                    </button>
                  )}
                {root.can_manage && onDelete && (
                  <button
                    type="button"
                    onClick={() => setDeleteRootId(root.id)}
                    aria-label="브랜치 폴더 삭제"
                    title="루트와 전체 브랜치 삭제"
                    className="inline-flex w-10 items-center justify-center rounded-xl border border-rose-300/20 bg-rose-300/5 text-rose-200/70 transition hover:bg-rose-300/10 hover:text-rose-100"
                  >
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>

      <DeleteConfirmModal
        isOpen={Boolean(deleteRootId)}
        title="브랜치 폴더 전체를 삭제하시겠습니까?"
        onCancel={() => setDeleteRootId(null)}
        onConfirm={async () => {
          if (deleteRootId) await onDelete?.(deleteRootId);
          setDeleteRootId(null);
        }}
      />
    </section>
  );
}

"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  FolderOpen,
  GitBranch,
  MessageSquare,
  Pencil,
  Search,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { InlineLoginPrompt } from "@/components/InlineLoginPrompt";
import { DeleteConfirmModal } from "@/components/DeleteConfirmModal";
import { getSupabaseToken } from "@/lib/apiFetch";
import { WorkspaceMembersModal } from "@/components/WorkspaceMembersModal";
import { WorkspaceModal } from "@/components/WorkspaceModal";
import {
  BranchNode,
  deleteThread,
  flattenBranchTree,
  listThreadBranches,
  updateThreadTitle,
} from "@/lib/threadApi";

export default function ThreadFolderPage() {
  const params = useParams<{ rootId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const rootId = Array.isArray(params.rootId) ? params.rootId[0] : params.rootId;
  const [token, setToken] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [threadSearch, setThreadSearch] = useState("");
  const [editingFolder, setEditingFolder] = useState(false);
  const [folderTitle, setFolderTitle] = useState("");
  const [folderBusy, setFolderBusy] = useState(false);
  const [folderError, setFolderError] = useState<string | null>(null);
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [nodeTitleDraft, setNodeTitleDraft] = useState("");
  const [nodeTitleBusy, setNodeTitleBusy] = useState(false);
  const [nodeTitleError, setNodeTitleError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<BranchNode | null>(null);
  const [deleteSuccessOpen, setDeleteSuccessOpen] = useState(false);
  const [workspaceCreateOpen, setWorkspaceCreateOpen] = useState(false);
  const [workspaceMembersOpen, setWorkspaceMembersOpen] = useState(false);
  const [returnToThreadsAfterDelete, setReturnToThreadsAfterDelete] =
    useState(false);

  useEffect(() => {
    let active = true;
    getSupabaseToken()
      .then((nextToken) => {
        if (active) setToken(nextToken);
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const { data, error, isLoading, refetch } = useQuery<{
    roots: BranchNode[];
  }>({
    queryKey: ["thread-branches", token],
    queryFn: () => listThreadBranches(token!),
    enabled: Boolean(token),
    retry: false,
  });

  const root = data?.roots.find((candidate) => candidate.id === rootId) || null;
  const nodes = useMemo(
    () => (root ? flattenBranchTree(root) : []),
    [root],
  );
  const normalizedSearch = threadSearch.trim().toLocaleLowerCase();
  const filteredNodes = useMemo(
    () =>
      normalizedSearch
        ? nodes.filter((node) =>
            (node.title || "")
              .toLocaleLowerCase()
              .includes(normalizedSearch),
          )
        : nodes,
    [nodes, normalizedSearch],
  );

  const saveFolderTitle = async () => {
    const title = folderTitle.trim();
    if (!token || !root || !title) {
      setFolderError("폴더명을 입력하세요.");
      return;
    }
    setFolderBusy(true);
    setFolderError(null);
    try {
      await updateThreadTitle(root.id, title, token);
      await Promise.all([
        refetch(),
        queryClient.invalidateQueries({ queryKey: ["threads"] }),
      ]);
      setEditingFolder(false);
    } catch (renameError) {
      setFolderError(
        renameError instanceof Error
          ? renameError.message
          : "폴더명을 수정하지 못했습니다.",
      );
    } finally {
      setFolderBusy(false);
    }
  };

  const removeNode = async (node: BranchNode) => {
    if (!token) return;
    await deleteThread(node.id, token);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["threads"] }),
      queryClient.invalidateQueries({ queryKey: ["thread-branches"] }),
    ]);
    if (node.id === rootId) {
      setReturnToThreadsAfterDelete(true);
      setDeleteSuccessOpen(true);
      return;
    }
    await refetch();
    setDeleteSuccessOpen(true);
  };

  const saveNodeTitle = async (node: BranchNode) => {
    const title = nodeTitleDraft.trim();
    if (!token || !title) {
      setNodeTitleError("스레드명을 입력하세요.");
      return;
    }
    setNodeTitleBusy(true);
    setNodeTitleError(null);
    try {
      await updateThreadTitle(node.id, title, token);
      await Promise.all([
        refetch(),
        queryClient.invalidateQueries({ queryKey: ["threads"] }),
      ]);
      setEditingNodeId(null);
      setNodeTitleDraft("");
    } catch (renameError) {
      setNodeTitleError(
        renameError instanceof Error
          ? renameError.message
          : "스레드명을 수정하지 못했습니다.",
      );
    } finally {
      setNodeTitleBusy(false);
    }
  };

  return (
    <main className="h-[100dvh] overflow-x-hidden overflow-y-auto bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] px-2 pb-[max(.5rem,env(safe-area-inset-bottom))] pt-[max(.5rem,env(safe-area-inset-top))] text-white sm:overflow-hidden sm:px-4 sm:py-4 md:px-8 md:py-6">
      <section className="mx-auto flex h-full max-w-6xl flex-col">
        <header className="mb-3 flex shrink-0 items-start gap-2 sm:mb-5 sm:gap-4">
          <button
            type="button"
            onClick={() => router.push("/threads")}
            aria-label="스레드 목록으로 돌아가기"
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-white transition hover:bg-white/10"
          >
            <ArrowLeft size={19} />
          </button>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-200/75">
              브랜치 폴더
            </p>
            <h1 className="mt-1 text-xl font-bold sm:text-2xl">폴더 스레드</h1>
            <label className="mt-2 flex min-h-11 max-w-2xl items-center gap-2 rounded-xl border border-white/15 bg-slate-950/30 px-3 py-2 text-blue-100 shadow-inner transition focus-within:border-cyan-300/45 focus-within:bg-slate-950/45 sm:mt-3 sm:gap-3 sm:rounded-2xl sm:px-4 sm:py-2.5">
              <Search size={17} className="shrink-0 text-cyan-200/70" />
              <input
                type="search"
                value={threadSearch}
                onChange={(event) => setThreadSearch(event.target.value)}
                placeholder="스레드명을 입력하세요"
                aria-label="폴더 내 스레드명 검색"
                className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-blue-100/45"
              />
            </label>
          </div>
        </header>

        {authLoading || isLoading ? (
          <div className="h-44 animate-pulse rounded-3xl border border-white/10 bg-white/5" />
        ) : !token ? (
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <InlineLoginPrompt
              title="브랜치 폴더를 열려면 로그인하세요"
              message="로그인하면 이 브랜치 폴더에 저장된 스레드를 확인할 수 있습니다."
            />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-300/25 bg-red-400/10 p-5 text-sm text-red-100">
            <p>{(error as Error).message || "폴더를 불러오지 못했습니다."}</p>
            <button
              type="button"
              onClick={() => void refetch()}
              className="mt-3 font-semibold underline underline-offset-4"
            >
              다시 시도
            </button>
          </div>
        ) : !root ? (
          <div className="rounded-2xl border border-amber-300/25 bg-amber-300/10 p-6 text-amber-100">
            존재하지 않거나 접근할 수 없는 브랜치 폴더입니다.
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col gap-3 sm:gap-5">
            <div className="relative shrink-0 overflow-visible rounded-2xl border border-amber-300/30 bg-gradient-to-br from-amber-300/15 via-orange-300/10 to-white/5 p-3 shadow-2xl shadow-amber-950/20 sm:rounded-3xl sm:p-5">
              <span
                aria-hidden="true"
                className="absolute -top-3 left-7 h-4 w-28 rounded-t-xl border-x border-t border-amber-300/35 bg-amber-300/20"
              />
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                <div className="flex min-w-0 items-center gap-3 sm:gap-4">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-amber-200/30 bg-amber-200/15 text-amber-200 sm:h-14 sm:w-14 sm:rounded-2xl">
                    <FolderOpen size={24} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-200/70">
                      Root thread folder
                    </p>
                    {editingFolder ? (
                      <div className="mt-1">
                        <div className="flex items-center gap-1.5">
                          <input
                            autoFocus
                            value={folderTitle}
                            maxLength={200}
                            disabled={folderBusy}
                            onChange={(event) =>
                              setFolderTitle(event.target.value)
                            }
                            onKeyDown={(event) => {
                              if (event.key === "Enter") {
                                event.preventDefault();
                                void saveFolderTitle();
                              } else if (event.key === "Escape") {
                                setEditingFolder(false);
                                setFolderError(null);
                              }
                            }}
                            aria-label="폴더명"
                            className="w-full min-w-0 rounded-lg border border-amber-200/30 bg-black/20 px-2.5 py-1 text-base font-bold text-white outline-none focus:ring-2 focus:ring-amber-200/30 sm:text-lg"
                          />
                          <button
                            type="button"
                            onClick={() => void saveFolderTitle()}
                            disabled={folderBusy}
                            aria-label="폴더명 저장"
                            className="rounded p-1.5 text-emerald-300 hover:bg-emerald-300/10 disabled:opacity-40"
                          >
                            {folderBusy ? (
                              <span className="block h-4 w-4 animate-spin rounded-full border-2 border-emerald-300 border-t-transparent" />
                            ) : (
                              <Check size={16} />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setEditingFolder(false);
                              setFolderError(null);
                            }}
                            disabled={folderBusy}
                            aria-label="폴더명 수정 취소"
                            className="rounded p-1.5 text-white/45 hover:bg-white/10 disabled:opacity-40"
                          >
                            <X size={16} />
                          </button>
                        </div>
                        {folderError && (
                          <p className="mt-1 text-xs text-rose-300">
                            {folderError}
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="mt-1 flex min-w-0 items-center gap-2">
                        <h2 className="min-w-0 truncate text-lg font-bold text-white sm:text-2xl">
                          {root.title || "제목 없는 스레드"}
                        </h2>
                        {root.can_manage && (
                          <button
                            type="button"
                            onClick={() => {
                              setFolderTitle(root.title || "");
                              setFolderError(null);
                              setEditingFolder(true);
                            }}
                            aria-label="폴더명 수정"
                            className="shrink-0 rounded p-1.5 text-white/40 transition hover:bg-amber-200/10 hover:text-amber-100"
                          >
                            <Pencil size={15} />
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {(root.is_workspace || root.can_manage_workspace) && (
                    <button
                      type="button"
                      onClick={() => {
                        if (root.is_workspace) {
                          setWorkspaceMembersOpen(true);
                        } else {
                          setWorkspaceCreateOpen(true);
                        }
                      }}
                      className="inline-flex min-h-10 min-w-32 flex-1 items-center justify-center gap-1.5 rounded-full border border-indigo-300/25 bg-indigo-300/10 px-2 py-2 text-xs font-bold text-indigo-100 transition hover:bg-indigo-300/20 sm:flex-none sm:px-3"
                    >
                      <Users size={14} />
                      {root.is_workspace ? "멤버 관리" : "워크스페이스로 전환"}
                    </button>
                  )}
                  <div className="flex min-h-10 min-w-24 flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-full border border-amber-200/20 bg-amber-200/10 px-2 py-2 text-xs font-semibold text-amber-50 sm:flex-none sm:gap-2 sm:px-4 sm:text-sm">
                    <GitBranch size={16} />
                    스레드 {nodes.length}개
                  </div>
                  {root.can_manage && (
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(root)}
                      aria-label="브랜치 폴더 전체 삭제"
                      title="루트와 전체 브랜치 삭제"
                      className="flex h-10 w-10 items-center justify-center rounded-full border border-rose-300/20 bg-rose-300/5 text-rose-200/70 transition hover:bg-rose-300/10 hover:text-rose-100"
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>
              </div>
            </div>

            <section className="flex min-h-0 flex-1 flex-col rounded-2xl border border-white/10 bg-white/5 p-3 backdrop-blur sm:rounded-3xl sm:p-5 md:p-6">
              <div className="mb-3 flex shrink-0 items-center justify-between sm:mb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-200/70">
                    저장된 스레드
                  </p>
                  <h2 className="mt-1 text-lg font-bold sm:text-xl">이 폴더의 스레드</h2>
                </div>
                <span className="text-xs text-white/45">루트 포함</span>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-0 sm:pr-2 [scrollbar-color:rgba(103,232,249,0.35)_rgba(15,23,42,0.35)] [scrollbar-width:thin]">
                <div className="grid gap-3 pb-1 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredNodes.map((node) => {
                    const isRoot = node.depth === 0;
                    return (
                      <article
                        key={node.id}
                        className={`flex min-h-36 flex-col rounded-2xl border border-white/10 bg-slate-950/35 p-3 shadow-lg transition sm:p-4 ${
                          node.is_deleted
                            ? "opacity-40 saturate-50"
                            : "hover:border-cyan-300/35 hover:bg-slate-950/50 sm:hover:-translate-y-0.5"
                        }`}
                      >
                      <div className="flex items-start gap-3">
                        <div
                          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
                            isRoot
                              ? "bg-amber-300/15 text-amber-200"
                              : "bg-cyan-300/10 text-cyan-200"
                          }`}
                        >
                          {isRoot ? (
                            <FolderOpen size={18} />
                          ) : (
                            <MessageSquare size={17} />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          {editingNodeId === node.id ? (
                            <div>
                              <div className="flex min-w-0 items-center gap-1">
                                <input
                                  autoFocus
                                  value={nodeTitleDraft}
                                  maxLength={200}
                                  disabled={nodeTitleBusy}
                                  onChange={(event) =>
                                    setNodeTitleDraft(event.target.value)
                                  }
                                  onKeyDown={(event) => {
                                    if (event.key === "Enter") {
                                      event.preventDefault();
                                      void saveNodeTitle(node);
                                    } else if (event.key === "Escape") {
                                      setEditingNodeId(null);
                                      setNodeTitleError(null);
                                    }
                                  }}
                                  aria-label="브랜치 스레드명"
                                  className="min-w-0 flex-1 rounded-lg border border-cyan-200/25 bg-black/25 px-2 py-1 text-sm font-semibold text-white outline-none focus:ring-2 focus:ring-cyan-200/30"
                                />
                                <button
                                  type="button"
                                  onClick={() => void saveNodeTitle(node)}
                                  disabled={nodeTitleBusy}
                                  aria-label="스레드명 저장"
                                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-emerald-300 transition hover:bg-emerald-300/10 disabled:opacity-40"
                                >
                                  {nodeTitleBusy ? (
                                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-300 border-t-transparent" />
                                  ) : (
                                    <Check size={15} />
                                  )}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingNodeId(null);
                                    setNodeTitleError(null);
                                  }}
                                  disabled={nodeTitleBusy}
                                  aria-label="스레드명 수정 취소"
                                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white/45 transition hover:bg-white/10 disabled:opacity-40"
                                >
                                  <X size={15} />
                                </button>
                              </div>
                              {nodeTitleError && (
                                <p className="mt-1 text-[10px] text-rose-300">
                                  {nodeTitleError}
                                </p>
                              )}
                            </div>
                          ) : (
                            <div className="flex min-w-0 items-start gap-1">
                              <h3 className="min-w-0 flex-1 line-clamp-2 text-sm font-semibold leading-5 text-white">
                                {node.title || "제목 없는 스레드"}
                              </h3>
                              {node.can_manage && !node.is_deleted && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingNodeId(node.id);
                                    setNodeTitleDraft(node.title || "");
                                    setNodeTitleError(null);
                                  }}
                                  aria-label={`${node.title || "제목 없는 스레드"} 제목 수정`}
                                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white/45 transition hover:bg-cyan-300/10 hover:text-cyan-100"
                                >
                                  <Pencil size={13} />
                                </button>
                              )}
                            </div>
                          )}
                          <p className="mt-2 truncate text-[10px] text-white/45">
                            {node.created_at
                              ? new Date(node.created_at).toLocaleString()
                              : ""}
                          </p>
                        </div>
                      </div>
                      <div className="mt-auto flex gap-2 pt-3">
                        <button
                          type="button"
                          disabled={Boolean(node.is_deleted)}
                          onClick={() => router.push(`/threads/${node.id}`)}
                          className="min-h-11 flex-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-bold text-white/85 transition hover:border-cyan-300/30 hover:bg-cyan-300/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:border-white/10 disabled:hover:bg-white/5"
                        >
                          {node.is_deleted ? "삭제된 스레드" : "스레드 열기"}
                        </button>
                        {node.can_manage && !node.is_deleted && (
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(node)}
                            aria-label={`${node.title || "제목 없는 스레드"} 삭제`}
                            className="flex h-11 w-11 items-center justify-center rounded-xl border border-rose-300/15 bg-rose-300/5 text-rose-200/70 transition hover:bg-rose-300/10 hover:text-rose-100"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                      </article>
                    );
                  })}
                </div>
                {filteredNodes.length === 0 && (
                  <div className="flex h-full min-h-40 items-center justify-center rounded-2xl border border-dashed border-white/15 bg-slate-950/20 px-5 text-center text-sm text-blue-100/65">
                    검색 조건과 일치하는 스레드가 없습니다.
                  </div>
                )}
              </div>
            </section>
          </div>
        )}
      </section>

      {workspaceCreateOpen && root && (
        <WorkspaceModal
          threadId={root.id}
          onClose={() => setWorkspaceCreateOpen(false)}
          onSuccess={() => {
            setWorkspaceCreateOpen(false);
            setWorkspaceMembersOpen(true);
            void refetch();
            void queryClient.invalidateQueries({ queryKey: ["threads"] });
          }}
        />
      )}

      {workspaceMembersOpen && root && (
        <WorkspaceMembersModal
          threadId={root.id}
          canManage={Boolean(root.can_manage_workspace)}
          onClose={() => setWorkspaceMembersOpen(false)}
        />
      )}

      <DeleteConfirmModal
        isOpen={Boolean(deleteTarget)}
        title={
          deleteTarget?.id === rootId
            ? "루트와 전체 브랜치를 삭제하시겠습니까?"
            : "이 스레드를 삭제하시겠습니까?"
        }
        onCancel={() => setDeleteTarget(null)}
        onConfirm={async () => {
          if (deleteTarget) await removeNode(deleteTarget);
          setDeleteTarget(null);
        }}
      />

      {deleteSuccessOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center overflow-y-auto bg-black/40 p-3 pb-[max(.75rem,env(safe-area-inset-bottom))] pt-[max(.75rem,env(safe-area-inset-top))] backdrop-blur-sm sm:px-6">
          <div
            role="status"
            aria-live="polite"
            className="w-full max-w-sm rounded-2xl border border-emerald-300/30 bg-slate-950/95 p-6 text-white shadow-2xl"
          >
            <p className="text-center text-base font-semibold">삭제되었습니다.</p>
            <div className="mt-5 flex justify-center">
              <button
                type="button"
                onClick={() => {
                  setDeleteSuccessOpen(false);
                  if (returnToThreadsAfterDelete) router.push("/threads");
                }}
                className="rounded-lg bg-emerald-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-emerald-400"
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

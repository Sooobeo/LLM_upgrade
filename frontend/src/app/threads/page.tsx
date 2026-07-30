"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { BranchFolderList } from "@/components/BranchFolderList";
import { NewThreadModal } from "@/components/NewThreadModal";
import { ThreadList } from "@/components/ThreadList";
import { InlineLoginPrompt } from "@/components/InlineLoginPrompt";
import { auth } from "@/lib/auth";
import {
  BranchNode,
  collectBranchThreadIds,
  deleteThread,
  fetchMembers,
  flattenBranchTree,
  listThreadBranches,
  listThreads,
  ThreadSummary,
  updateThreadTitle,
} from "@/lib/threadApi";
import { supabase } from "@/lib/supabaseClient";
import { getSupabaseToken } from "@/lib/apiFetch";
import { WorkspaceModal } from "@/components/WorkspaceModal";
import { WorkspaceMembersModal } from "@/components/WorkspaceMembersModal";

export default function ThreadsPage() {
  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [deleteSuccessOpen, setDeleteSuccessOpen] = useState(false);
  const [workspaceThreadId, setWorkspaceThreadId] = useState<string | null>(null);
  const [membersThreadId, setMembersThreadId] = useState<string | null>(null);
  const [threadSearch, setThreadSearch] = useState("");

  useEffect(() => {
    let active = true;
    getSupabaseToken()
      .then((t) => {
        if (!active) return;
        setToken(t);
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });
    const { data: subscription } = supabase
      ? supabase.auth.onAuthStateChange((_event, session) => {
          if (!active) return;
          const next = session?.access_token;
          // Hosted Google OAuth lives in the backend's HttpOnly refresh
          // cookie. The non-persistent browser client emits an initial null
          // session, which must not overwrite the restored backend session.
          if (!next) return;
          auth.setToken(next);
          setToken(next);
          setAuthLoading(false);
        })
      : { data: null };
    return () => {
      active = false;
      subscription?.subscription.unsubscribe();
    };
  }, [router]);

  const { data, isLoading, error, refetch } = useQuery<ThreadSummary[]>({
    queryKey: ["threads", token],
    queryFn: () => listThreads({ limit: 100, offset: 0, order: "desc" }, token!),
    enabled: !!token,
    retry: false,
  });

  const {
    data: branchData,
    isLoading: branchesLoading,
    error: branchesError,
  } = useQuery<{ roots: BranchNode[] }>({
    queryKey: ["thread-branches", token],
    queryFn: () => listThreadBranches(token!),
    enabled: !!token,
    retry: false,
  });

  const threads = useMemo(() => data || [], [data]);
  const branchRoots = useMemo(
    () => branchData?.roots || [],
    [branchData?.roots],
  );
  const branchThreadIds = useMemo(
    () => collectBranchThreadIds(branchRoots),
    [branchRoots],
  );
  const standaloneThreads = useMemo(
    () =>
      branchesError
        ? threads
        : threads.filter((thread) => !branchThreadIds.has(thread.id)),
    [branchThreadIds, branchesError, threads],
  );
  const normalizedSearch = threadSearch.trim().toLocaleLowerCase();
  const filteredBranchRoots = useMemo(
    () =>
      normalizedSearch
        ? branchRoots.filter((root) =>
            flattenBranchTree(root).some((node) =>
              (node.title || "")
                .toLocaleLowerCase()
                .includes(normalizedSearch),
            ),
          )
        : branchRoots,
    [branchRoots, normalizedSearch],
  );
  const filteredStandaloneThreads = useMemo(
    () =>
      normalizedSearch
        ? standaloneThreads.filter((thread) =>
            (thread.title || "")
              .toLocaleLowerCase()
              .includes(normalizedSearch),
          )
        : standaloneThreads,
    [normalizedSearch, standaloneThreads],
  );

  const logout = async () => {
    const currentToken = auth.getToken();
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
        headers: currentToken ? { Authorization: `Bearer ${currentToken}` } : {},
      });
    } catch {
      // Clear local in-memory state even if the server is temporarily unavailable.
    }
    auth.clear();
    await supabase?.auth.signOut();
    router.push("/login");
  };

  const queryClient = useQueryClient();

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white">
      <div className="mx-auto max-w-5xl px-4 py-12">
        {/* ===== Glass Card ===== */}
        <div className="rounded-3xl border border-white/15 bg-white/5 backdrop-blur-xl px-6 py-8 md:px-10 md:py-10">
          {/* ===== Header ===== */}
          <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-200">
                Chat archive
              </p>
              <h1 className="text-3xl font-bold text-white md:text-4xl">
                Archived conversations
              </h1>
              <p className="text-sm text-blue-100">
                저장한 대화와 브랜치 폴더를 찾고, 새로운 흐름을 시작하세요.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => router.push("/branch-zip")}
                className="rounded-xl border border-cyan-300/30 bg-cyan-400/10 px-4 py-2 text-sm font-semibold text-cyan-50 backdrop-blur transition hover:border-cyan-300/50 hover:bg-cyan-400/20"
              >
                branch-zip
              </button>
              <button
                onClick={logout}
                className="rounded-xl border border-white/20 bg-white/5 px-4 py-2 text-sm font-semibold text-white backdrop-blur transition hover:bg-white/10"
              >
                Logout
              </button>
              <button
                onClick={() => setIsModalOpen(true)}
                className="rounded-xl bg-gradient-to-r from-blue-500 to-cyan-400 px-5 py-2 text-sm font-semibold text-white shadow transition hover:-translate-y-0.5 hover:shadow-lg"
              >
                New Thread
              </button>
            </div>
          </header>

          <label className="mb-6 flex items-center gap-3 rounded-2xl border border-white/15 bg-slate-950/30 px-4 py-3 text-blue-100 shadow-inner transition focus-within:border-cyan-300/45 focus-within:bg-slate-950/45">
            <Search size={18} className="shrink-0 text-cyan-200/70" />
            <input
              type="search"
              value={threadSearch}
              onChange={(event) => setThreadSearch(event.target.value)}
              placeholder="스레드명을 입력하세요"
              aria-label="스레드명 검색"
              className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-blue-100/45"
            />
          </label>

          {/* ===== Content ===== */}
          {authLoading ? (
            <div className="rounded-2xl border border-white/15 bg-white/5 p-6 text-sm text-blue-100 backdrop-blur">
              로그인 상태를 확인하는 중입니다...
            </div>
          ) : !token ? (
            <div className="rounded-2xl border border-white/15 bg-white/5 p-6 backdrop-blur">
              <InlineLoginPrompt
                title="Sign in to view your threads"
                message="Login to load your threads and continue."
              />
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200 backdrop-blur">
              <p>{(error as any)?.message || "스레드를 불러오지 못했습니다."}</p>
              <button
                type="button"
                onClick={() => refetch()}
                className="mt-3 rounded-lg border border-red-200/30 px-3 py-1.5 text-xs font-semibold hover:bg-red-400/10"
              >
                다시 시도
              </button>
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
              {branchesError && (
                <div className="mb-5 rounded-xl border border-amber-300/25 bg-amber-300/10 px-4 py-3 text-sm text-amber-100">
                  브랜치 폴더를 불러오지 못해 모든 스레드를 일반 목록으로 표시합니다.
                </div>
              )}

              {!branchesError && (
                <BranchFolderList
                  roots={filteredBranchRoots}
                  onOpen={(rootId) =>
                    router.push(`/thread-folders/${rootId}`)
                  }
                  onRename={async (rootId, title) => {
                    if (!token) return;
                    await updateThreadTitle(rootId, title, token);
                    queryClient.setQueryData<{ roots: BranchNode[] }>(
                      ["thread-branches", token],
                      (previous) =>
                        previous
                          ? {
                              roots: previous.roots.map((root) =>
                                root.id === rootId
                                  ? { ...root, title }
                                  : root,
                              ),
                            }
                          : previous,
                    );
                    void queryClient.invalidateQueries({
                      queryKey: ["threads"],
                    });
                  }}
                  onDelete={async (rootId) => {
                    if (!token) return;
                    await deleteThread(rootId, token);
                    queryClient.setQueryData<{ roots: BranchNode[] }>(
                      ["thread-branches", token],
                      (previous) =>
                        previous
                          ? {
                              roots: previous.roots.filter(
                                (root) => root.id !== rootId,
                              ),
                            }
                          : previous,
                    );
                    await Promise.all([
                      queryClient.invalidateQueries({
                        queryKey: ["thread-branches"],
                      }),
                      queryClient.invalidateQueries({
                        queryKey: ["threads"],
                      }),
                    ]);
                    setDeleteSuccessOpen(true);
                  }}
                />
              )}

              <ThreadList
                threads={filteredStandaloneThreads}
                isLoading={isLoading || branchesLoading}
                onSelect={(id) => router.push(`/threads/${id}`)}
                onDelete={async (id) => {
                  if (!token) return;
                  try {
                    await deleteThread(id, token);
                    queryClient.setQueryData<ThreadSummary[]>(
                      ["threads", token],
                      (previous) => previous?.filter((thread) => thread.id !== id),
                    );
                    setDeleteSuccessOpen(true);
                    void refetch();
                  } catch (e: any) {
                    alert(e?.message || "삭제에 실패했습니다.");
                    throw e;
                  }
                }}
                onRename={async (id, title) => {
                  if (!token) return;
                  const updated = await updateThreadTitle(id, title, token);
                  queryClient.setQueryData<ThreadSummary[]>(
                    ["threads", token],
                    (previous) =>
                      previous?.map((thread) =>
                        thread.id === id
                          ? { ...thread, title: updated.title }
                          : thread,
                      ),
                  );
                  void queryClient.invalidateQueries({
                    queryKey: ["thread-branches"],
                  });
                }}
                onWorkspace={async (thread) => {
                  try {
                    const members = await fetchMembers(thread.id);

                    if (members.length <= 1) {
                      setWorkspaceThreadId(thread.id);
                    } else {
                      setMembersThreadId(thread.id);
                    }
                  } catch {
                    alert("워크스페이스 정보를 불러오지 못했습니다.");
                  }
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* ===== Modals ===== */}
      <NewThreadModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        token={token}
        onCreated={() => {
          refetch();
        }}
      />

      {workspaceThreadId && token && (
        <WorkspaceModal
          threadId={workspaceThreadId}
          onClose={() => setWorkspaceThreadId(null)}
          onSuccess={(threadId) => {
            queryClient.setQueryData<ThreadSummary[]>(["threads", token], (prev) =>
              prev?.map(t =>
                t.id === threadId ? { ...t, is_workspace: true } : t
              )
            );
            refetch();
            setWorkspaceThreadId(null);
            setMembersThreadId(threadId); 
          }}
        />
      )}

      {membersThreadId && (
        <WorkspaceMembersModal
          threadId={membersThreadId}
          onClose={() => setMembersThreadId(null)}
        />
      )}

      {deleteSuccessOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 px-6 backdrop-blur-sm">
          <div
            role="status"
            aria-live="polite"
            className="w-full max-w-sm rounded-2xl border border-emerald-300/30 bg-slate-950/95 p-6 text-white shadow-2xl"
          >
            <p className="text-center text-base font-semibold">삭제되었습니다.</p>
            <div className="mt-5 flex justify-center">
              <button
                type="button"
                onClick={() => setDeleteSuccessOpen(false)}
                className="rounded-lg bg-emerald-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-emerald-400"
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

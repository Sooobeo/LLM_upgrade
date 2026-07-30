"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BranchTree } from "@/components/BranchTree";
import { getSupabaseToken } from "@/lib/apiFetch";
import {
  BranchNode,
  deleteThread,
  listThreadBranches,
} from "@/lib/threadApi";
import { DeleteConfirmModal } from "@/components/DeleteConfirmModal";

export default function BranchZipPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [token, setToken] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [expandedRootId, setExpandedRootId] = useState<string | null>(null);
  const [deleteRoot, setDeleteRoot] = useState<BranchNode | null>(null);
  const [deleteSuccessOpen, setDeleteSuccessOpen] = useState(false);

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

  const { data, error, isLoading, refetch } = useQuery<{ roots: BranchNode[] }>({
    queryKey: ["thread-branches", token],
    queryFn: () => listThreadBranches(token!),
    enabled: Boolean(token),
    retry: false,
  });

  const roots = data?.roots ?? [];
  const expandedRoot =
    roots.find((root) => root.id === expandedRootId) ?? null;

  const removeNode = async (node: BranchNode) => {
    if (!token) return;
    await deleteThread(node.id, token);
    if (node.id === expandedRootId || node.id === expandedRoot?.id) {
      setExpandedRootId(null);
    }
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["thread-branches"] }),
      queryClient.invalidateQueries({ queryKey: ["threads"] }),
    ]);
    await refetch();
    setDeleteSuccessOpen(true);
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] p-4 text-white md:p-8">
      <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[1600px] flex-col overflow-hidden rounded-3xl border border-white/15 bg-white/5 shadow-2xl backdrop-blur-xl">
        <header className="flex items-start gap-4 border-b border-white/10 px-6 py-5">
          <button
            type="button"
            onClick={() => router.push("/threads")}
            aria-label="스레드 목록으로 돌아가기"
            title="스레드 목록으로 돌아가기"
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/20 bg-white/5 text-xl font-semibold text-white transition hover:bg-white/10"
          >
            <ArrowLeft size={19} />
          </button>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
              브랜치 시각화
            </p>
            <h1 className="mt-1 text-2xl font-bold text-white">branch-zip</h1>
            <p className="mt-1 text-sm text-blue-100">
              Gemini 스레드가 분기된 흐름을 왼쪽에서 오른쪽으로 확인하세요.
            </p>
          </div>
        </header>

        <div className="grid min-h-0 flex-1 md:grid-cols-[300px_minmax(0,1fr)]">
          <aside className="flex min-h-0 flex-col border-b border-white/10 bg-slate-950/25 p-4 md:border-b-0 md:border-r">
            <div className="flex items-center justify-between px-2">
              <h2 className="text-xs font-semibold tracking-[0.16em] text-blue-200">
                루트 스레드
              </h2>
              {!authLoading && token && (
                <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2 py-0.5 text-[10px] font-semibold text-cyan-100">
                  {roots.length}개
                </span>
              )}
            </div>

            <div className="mt-4 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1 [scrollbar-color:rgba(103,232,249,0.35)_rgba(15,23,42,0.35)] [scrollbar-width:thin]">
              {authLoading || isLoading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-14 animate-pulse rounded-xl border border-white/10 bg-white/5"
                  />
                ))
              ) : !token ? (
                <div className="rounded-xl border border-amber-300/25 bg-amber-400/10 p-4 text-sm text-amber-100">
                  <p>로그인 후 브랜치 트리를 확인할 수 있습니다.</p>
                  <button
                    type="button"
                    onClick={() => router.push("/login")}
                    className="mt-3 font-semibold underline underline-offset-4"
                  >
                    로그인하기
                  </button>
                </div>
              ) : error ? (
                <div className="rounded-xl border border-red-300/25 bg-red-400/10 p-4 text-sm text-red-100">
                  <p>{(error as Error).message || "브랜치 트리를 불러오지 못했습니다."}</p>
                  <button
                    type="button"
                    onClick={() => void refetch()}
                    className="mt-3 font-semibold underline underline-offset-4"
                  >
                    다시 시도
                  </button>
                </div>
              ) : roots.length === 0 ? (
                <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-blue-100">
                  아직 생성된 Gemini 브랜치가 없습니다. Gemini 스레드에서
                  브랜치를 만들어 보세요.
                </div>
              ) : (
                roots.map((root) => {
                  const isExpanded = expandedRootId === root.id;
                  return (
                    <div key={root.id} className="flex items-stretch gap-1.5">
                      <button
                        type="button"
                        aria-expanded={isExpanded}
                        onClick={() =>
                          setExpandedRootId((current) =>
                            current === root.id ? null : root.id,
                          )
                        }
                        className={`flex min-w-0 flex-1 items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm font-semibold transition ${
                          isExpanded
                            ? "border-cyan-300/50 bg-cyan-400/15 text-white shadow-lg shadow-cyan-950/20"
                            : "border-white/10 bg-white/5 text-blue-50 hover:border-white/20 hover:bg-white/10"
                        }`}
                      >
                        <span className="min-w-0 flex-1 truncate">
                          {root.title || "제목 없는 스레드"}
                        </span>
                        <span
                          aria-hidden="true"
                          className={`h-0 w-0 shrink-0 border-y-[6px] border-l-[9px] border-y-transparent border-l-cyan-300 transition-transform ${
                            isExpanded ? "rotate-90" : ""
                          }`}
                        />
                      </button>
                      {root.can_manage && (
                        <button
                          type="button"
                          onClick={() => setDeleteRoot(root)}
                          aria-label={`${root.title || "제목 없는 스레드"} 폴더 삭제`}
                          title="폴더와 전체 브랜치 삭제"
                          className="inline-flex w-10 shrink-0 items-center justify-center rounded-xl border border-rose-300/20 bg-rose-300/5 text-rose-200/70 transition hover:bg-rose-300/10 hover:text-rose-100"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </aside>

          <section className="min-h-[520px] min-w-0 bg-[radial-gradient(circle_at_top_left,rgba(37,99,235,0.12),transparent_42%)]">
            {expandedRoot ? (
              <div className="h-full min-h-[520px] overflow-hidden p-3 md:p-4">
                <BranchTree
                  root={expandedRoot}
                  token={token!}
                  onSelect={(threadId) => router.push(`/threads/${threadId}`)}
                  onDelete={removeNode}
                />
              </div>
            ) : (
              <div className="flex h-full min-h-[520px] items-center justify-center p-8 text-center">
                <div>
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-300/20 bg-cyan-400/10">
                    <span className="h-0 w-0 border-y-[10px] border-l-[15px] border-y-transparent border-l-cyan-300" />
                  </div>
                  <h2 className="mt-5 text-lg font-semibold text-white">
                    루트 스레드를 선택하세요
                  </h2>
                  <p className="mt-2 max-w-sm text-sm leading-6 text-blue-100">
                    왼쪽 목록에서 루트 스레드를 누르면 전체 브랜치 트리가
                    펼쳐집니다.
                  </p>
                </div>
              </div>
            )}
          </section>
        </div>
      </section>

      <DeleteConfirmModal
        isOpen={Boolean(deleteRoot)}
        title="브랜치 폴더 전체를 삭제하시겠습니까?"
        description="루트 스레드와 연결된 전체 브랜치가 함께 삭제됩니다."
        onCancel={() => setDeleteRoot(null)}
        onConfirm={async () => {
          if (deleteRoot) await removeNode(deleteRoot);
          setDeleteRoot(null);
        }}
      />

      {deleteSuccessOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 px-6 backdrop-blur-sm">
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
    </main>
  );
}

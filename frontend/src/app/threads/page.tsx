"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { NewThreadModal } from "@/components/NewThreadModal";
import { ThreadList } from "@/components/ThreadList";
import { InlineLoginPrompt } from "@/components/InlineLoginPrompt";
import { auth } from "@/lib/auth";
import { listThreads, ThreadSummary, deleteThread, createWorkspace } from "@/lib/threadApi";
import { supabase } from "@/lib/supabaseClient";
import { getSupabaseToken } from "@/lib/apiFetch";
import { WorkspaceModal } from "@/components/WorkspaceModal";
import { WorkspaceMembersModal } from "@/components/WorkspaceMembersModal";
import { fetchMembers } from "@/lib/threadApi";

export default function ThreadsPage() {
  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [workspaceThreadId, setWorkspaceThreadId] = useState<string | null>(null);
  const [membersThreadId, setMembersThreadId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getSupabaseToken().then((t) => {
      if (!active) return;
      setToken(t);
    });
    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!active) return;
      const next = session?.access_token || null;
      if (next) auth.setSession({ accessToken: next, refreshToken: session?.refresh_token || undefined });
      setToken(next);
    });
    return () => {
      active = false;
      subscription?.subscription.unsubscribe();
    };
  }, [router]);

  const { data, isLoading, error, refetch } = useQuery<ThreadSummary[]>({
    queryKey: ["threads"],
    queryFn: () => listThreads({ limit: 20, offset: 0, order: "desc" }, token!),
    enabled: !!token,
  });

  const threads = data || [];

  const logout = async () => {
    auth.clear();
    await supabase.auth.signOut();
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
                Threads
              </p>
              <h1 className="text-3xl font-bold text-white md:text-4xl">
                Your conversations
              </h1>
              <p className="text-sm text-blue-100">
                Manage threads, start a new chat, and jump back into workspaces.
              </p>
            </div>

            <div className="flex items-center gap-2">
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

          {/* ===== Content ===== */}
          {!token ? (
            <div className="rounded-2xl border border-white/15 bg-white/5 p-6 backdrop-blur">
              <InlineLoginPrompt
                title="Sign in to view your threads"
                message="Login to load your threads and continue."
              />
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200 backdrop-blur">
              {(error as any)?.message || "스레드를 불러오지 못했습니다."}
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">

              <ThreadList
                threads={threads}
                isLoading={isLoading}
                onSelect={(id) => router.push(`/threads/${id}`)}
                onNew={() => setIsModalOpen(true)}
                onDelete={async (id) => {
                  if (!token) return;
                  try {
                    await deleteThread(id, token);
                    refetch();
                  } catch (e: any) {
                    alert(e?.message || "삭제에 실패했습니다.");
                  }
                }}
                onWorkspace={async (thread) => {
                  try {
                    const members = await fetchMembers(thread.id);

                    if (members.length <= 1) {
                      setWorkspaceThreadId(thread.id);
                    } else {
                      setMembersThreadId(thread.id);
                    }
                  } catch (e) {
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
            queryClient.setQueryData<ThreadSummary[]>(["threads"], (prev) =>
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
    </div>
  );
}
"use client";

import { useQuery } from "@tanstack/react-query";
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
import { useCurrentUser } from "@/hooks/useCurrentUser";

export default function ThreadsPage() {
  const router = useRouter();
  const { user } = useCurrentUser({ redirectIfMissing: false });
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

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-5xl px-4 py-10">
        <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Threads</p>
            <h1 className="text-3xl font-bold text-slate-900">Your conversations</h1>
            <p className="text-sm text-slate-600">
              Manage threads, start a new chat, and jump back into workspaces.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {user?.email && (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                {user.email}
              </span>
            )}
            <button
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-800 shadow-sm hover:bg-slate-100"
              onClick={logout}
            >
              Logout
            </button>
          </div>
        </header>

        {!token ? (
          <InlineLoginPrompt title="Sign in to view your threads" message="Login to load your threads and continue." />
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {(error as any)?.message || "스레드를 불러오지 못했습니다."}
          </div>
        ) : (
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
        onWorkspace={(id) => setWorkspaceThreadId(id)}
        onMembers={(id) => setMembersThreadId(id)}
      />
        )}
      </div>

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
          onSuccess={() => {
            refetch();
          }}
        />
      )}

      {membersThreadId && (
        <WorkspaceMembersModal threadId={membersThreadId} onClose={() => setMembersThreadId(null)} />
      )}
    </div>
  );
}

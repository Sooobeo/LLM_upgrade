"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BranchTree } from "@/components/BranchTree";
import { getSupabaseToken } from "@/lib/apiFetch";
import { BranchNode, listThreadBranches } from "@/lib/threadApi";

export default function BranchZipPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [expandedRootId, setExpandedRootId] = useState<string | null>(null);

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

  return (
    <main className="min-h-screen bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] p-4 text-white md:p-8">
      <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[1600px] flex-col overflow-hidden rounded-3xl border border-white/15 bg-white/5 shadow-2xl backdrop-blur-xl">
        <header className="flex items-start gap-4 border-b border-white/10 px-6 py-5">
          <button
            type="button"
            onClick={() => router.push("/threads")}
            aria-label="Move to threads"
            title="Move to threads"
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/20 bg-white/5 text-xl font-semibold text-white transition hover:bg-white/10"
          >
            ←
          </button>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
              Branch visualization
            </p>
            <h1 className="mt-1 text-2xl font-bold text-white">branch-zip</h1>
            <p className="mt-1 text-sm text-blue-100">
              Gemini conversations and their branches, from left to right.
            </p>
          </div>
        </header>

        <div className="grid min-h-0 flex-1 md:grid-cols-[300px_minmax(0,1fr)]">
          <aside className="border-b border-white/10 bg-slate-950/25 p-4 md:border-b-0 md:border-r">
            <h2 className="px-2 text-xs font-semibold uppercase tracking-[0.2em] text-blue-200">
              Root threads
            </h2>

            <div className="mt-4 space-y-2">
              {authLoading || isLoading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-14 animate-pulse rounded-xl border border-white/10 bg-white/5"
                  />
                ))
              ) : !token ? (
                <div className="rounded-xl border border-amber-300/25 bg-amber-400/10 p-4 text-sm text-amber-100">
                  <p>Sign in to view branch trees.</p>
                  <button
                    type="button"
                    onClick={() => router.push("/login")}
                    className="mt-3 font-semibold underline underline-offset-4"
                  >
                    Go to login
                  </button>
                </div>
              ) : error ? (
                <div className="rounded-xl border border-red-300/25 bg-red-400/10 p-4 text-sm text-red-100">
                  <p>{(error as Error).message || "Could not load branch trees."}</p>
                  <button
                    type="button"
                    onClick={() => void refetch()}
                    className="mt-3 font-semibold underline underline-offset-4"
                  >
                    Try again
                  </button>
                </div>
              ) : roots.length === 0 ? (
                <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-blue-100">
                  No Gemini branch trees yet. Open a Gemini thread and create its
                  first branch.
                </div>
              ) : (
                roots.map((root) => {
                  const isExpanded = expandedRootId === root.id;
                  return (
                    <button
                      key={root.id}
                      type="button"
                      aria-expanded={isExpanded}
                      onClick={() =>
                        setExpandedRootId((current) =>
                          current === root.id ? null : root.id,
                        )
                      }
                      className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm font-semibold transition ${
                        isExpanded
                          ? "border-cyan-300/50 bg-cyan-400/15 text-white shadow-lg shadow-cyan-950/20"
                          : "border-white/10 bg-white/5 text-blue-50 hover:border-white/20 hover:bg-white/10"
                      }`}
                    >
                      <span className="min-w-0 flex-1 truncate">
                        {root.title || "Untitled thread"}
                      </span>
                      <span
                        aria-hidden="true"
                        className={`h-0 w-0 shrink-0 border-y-[6px] border-l-[9px] border-y-transparent border-l-cyan-300 transition-transform ${
                          isExpanded ? "rotate-90" : ""
                        }`}
                      />
                    </button>
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
                />
              </div>
            ) : (
              <div className="flex h-full min-h-[520px] items-center justify-center p-8 text-center">
                <div>
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-300/20 bg-cyan-400/10">
                    <span className="h-0 w-0 border-y-[10px] border-l-[15px] border-y-transparent border-l-cyan-300" />
                  </div>
                  <h2 className="mt-5 text-lg font-semibold text-white">
                    Select a root thread
                  </h2>
                  <p className="mt-2 max-w-sm text-sm leading-6 text-blue-100">
                    Use the triangle beside a root thread to expand its complete
                    branch tree.
                  </p>
                </div>
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

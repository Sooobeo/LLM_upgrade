"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { getModel, setModel } from "@/lib/modelStore";
import { ChatMessage, getThread, postChat } from "@/lib/threadApi";
import { getSupabaseToken } from "@/lib/apiFetch";
import { ThreadSearchBar } from "./ThreadSearchBar";
import { supabase } from "@/lib/supabaseClient";
import { auth } from "@/lib/auth";
import { InlineLoginPrompt } from "./InlineLoginPrompt";

const MODEL_OPTIONS = ["gemma3:270m", "llama3.1:8b", "mistral:7b"];
const UUID_REGEX = /^[0-9a-fA-F-]{36}$/;

export function ChatView() {
  const params = useParams();
  const threadId = params?.threadId ? String(params.threadId) : "";
  const queryClient = useQueryClient();
  const [composer, setComposer] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pendingAssistantIndex, setPendingAssistantIndex] = useState<number | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [matchIndex, setMatchIndex] = useState(0);
  const [matches, setMatches] = useState<number[]>([]);
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState(() => getModel(threadId, MODEL_OPTIONS[0]));
  const [debugInfo, setDebugInfo] = useState<{
    url?: string;
    status?: number;
    bodySnippet?: string;
    hasToken?: boolean;
  }>({});
  const [token, setToken] = useState<string | null>(null);
  const hasToken = !!token;

  useEffect(() => {
    let active = true;
    getSupabaseToken().then((t) => {
      if (active) setToken(t);
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
  }, []);

  const isValidThreadId = useMemo(() => UUID_REGEX.test(threadId), [threadId]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["thread", threadId],
    queryFn: () =>
      getThread(
        threadId,
        token!,
        (info) =>
        setDebugInfo((prev) => ({
          ...prev,
          url: info.url,
          status: info.status,
          bodySnippet: info.bodySnippet,
          hasToken: info.hasAuth,
        })),
      ),
    retry: false,
    enabled: isValidThreadId && !!token,
  });

  useEffect(() => {
    if (data?.messages) {
      setMessages(data.messages);
    }
  }, [data?.messages]);

  const chatMutation = useMutation({
    mutationFn: async (content: string) => {
      setSendError(null);
      if (!isValidThreadId) {
        throw Object.assign(new Error("Invalid thread id"), { status: 400 });
      }
      if (!token) {
        const err: any = new Error("NO_TOKEN");
        err.status = 401;
        err.code = "NO_TOKEN";
        throw err;
      }
      return postChat(
        threadId,
        {
          content,
          model: selectedModel,
          context_limit: 50,
        },
        token,
        (info) =>
          setDebugInfo((prev) => ({
            ...prev,
            url: info.url,
            status: info.status,
            bodySnippet: info.bodySnippet,
            hasToken: info.hasAuth,
          })),
      );
    },
    onSuccess: (resp) => {
      // Replace placeholder assistant message with the real one
      setMessages((prev) => {
        const updated = [...prev];
        if (pendingAssistantIndex != null && updated[pendingAssistantIndex]) {
          updated[pendingAssistantIndex] = {
            role: "assistant",
            content: resp.assistant_content || "",
            created_at: new Date().toISOString(),
          };
        } else {
          updated.push({ role: "assistant", content: resp.assistant_content || "" });
        }
        return updated;
      });
      setPendingAssistantIndex(null);
      setComposer("");
      setDebugInfo((prev) => ({ ...prev, status: 200, bodySnippet: resp?.assistant_content, hasToken: true }));
      // refresh cache later to stay in sync
      queryClient.invalidateQueries({ queryKey: ["thread", threadId] });
    },
    onError: async (err: any) => {
      setPendingAssistantIndex(null);
      setMessages((prev) => prev.filter((_, idx) => idx !== pendingAssistantIndex));
      const masked404 =
        err?.status === 404
          ? "Thread not found or no access (masked 404). Check token and thread id."
          : null;
      const invalidId = err?.message === "Invalid thread id" ? err?.message : null;
      const noToken = err?.code === "NO_TOKEN" ? "Not logged in" : null;
      const message = noToken || invalidId || masked404 || err?.message || "??? ??? ??????.";
      setSendError(message);

      setDebugInfo((prev) => ({
        ...prev,
        status: err?.status,
        bodySnippet: err?.bodySnippet || err?.payload || err?.message,
      }));
      alert(message);
    },
  });

  const handleSend = () => {
    if (!composer.trim()) return;
    const content = composer.trim();
    if (process.env.NODE_ENV !== "production") {
      console.log("sending content", content, "threadId", threadId);
    }
    const userMsg: ChatMessage = { role: "user", content, created_at: new Date().toISOString() };
    const assistantPlaceholder: ChatMessage = {
      role: "assistant",
      content: "Generating...",
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => {
      const next = [...prev, userMsg, assistantPlaceholder];
      setPendingAssistantIndex(next.length - 1);
      return next;
    });
    chatMutation.mutate(content);
  };

  const runSearch = () => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) {
      setMatches([]);
      setMatchIndex(0);
      return;
    }
    const found = messages
      .map((m, idx) => (m.content.toLowerCase().includes(q) ? idx : -1))
      .filter((idx) => idx >= 0);
    setMatches(found);
    setMatchIndex(0);
    if (found.length > 0) {
      scrollToMatch(found[0]);
    }
  };

  const scrollToMatch = (idx: number) => {
    const el = document.getElementById(`msg-${idx}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      setHighlighted(idx);
      setTimeout(() => setHighlighted(null), 1200);
    }
  };

  const goPrev = () => {
    if (!matches.length) return;
    const next = (matchIndex - 1 + matches.length) % matches.length;
    setMatchIndex(next);
    scrollToMatch(matches[next]);
  };

  const goNext = () => {
    if (!matches.length) return;
    const next = (matchIndex + 1) % matches.length;
    setMatchIndex(next);
    scrollToMatch(matches[next]);
  };

  const title = data?.title || "Thread";

  if (!isValidThreadId) {
    return (
      <div className="flex h-full flex-col gap-2 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">
        <div className="font-semibold">Invalid thread id</div>
        <div className="text-sm">The provided thread id is not a valid UUID.</div>
        {process.env.NODE_ENV !== "production" && (
          <div className="text-xs text-red-600">threadId: {threadId || "<empty>"}</div>
        )}
      </div>
    );
  }

  if (!token) {
    return <InlineLoginPrompt title="Sign in to view this thread" message="Login to load messages and continue." />;
  }

  if (isLoading) {
    return <div className="flex h-full items-center justify-center text-slate-600">스레드를 불러오는 중...</div>;
  }

  if ((error as any)?.status === 401) {
    return <InlineLoginPrompt title="Session expired" message="Please sign in again to view this thread." />;
  }

  if ((error as any)?.status === 404) {
    return (
      <div className="flex h-full items-center justify-center text-slate-700">
        Not found or no access.
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center text-red-600">
        {(error as any)?.message || "스레드 로드 실패"}
      </div>
    );
  }

  return (
  <div className="fixed inset-0 overflow-hidden bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white">
    <div className="mx-auto flex h-full max-w-5xl flex-col gap-4 p-10">
      {/* Header */}
      <header className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-3 p-2">
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                if (typeof window !== "undefined") {
                  window.location.href = "/threads";
                }
              }}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm font-semibold text-white/80 hover:bg-white/10"
            >
              ←
            </button>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/50">
                Thread
              </p>
              <h1 className="text-xl font-bold text-white/90">
                {title || "Untitled"}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-white/60">Model</label>
            <select
              value={selectedModel}
              onChange={(e) => {
                setSelectedModel(e.target.value);
                setModel(threadId, e.target.value);
              }}
              className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-sm text-white focus:outline-none"
            >
              {MODEL_OPTIONS.map((m) => (
                <option key={m} value={m} className="text-black">
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>

        <ThreadSearchBar
          query={searchQuery}
          onQueryChange={setSearchQuery}
          onSubmit={runSearch}
          matchIndex={matchIndex}
          totalMatches={matches.length}
          onPrev={goPrev}
          onNext={goNext}
        />
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur shadow-lg">
        <div className="space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              id={`msg-${idx}`}
              className={`flex ${
                m.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm shadow-md ${
                  m.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-white/10 text-white/90"
                } ${highlighted === idx ? "ring-2 ring-amber-400" : ""}`}
              >
                <div className="text-[11px] uppercase tracking-wide opacity-60">
                  {m.role}
                </div>
                <div className="mt-1 whitespace-pre-wrap leading-relaxed">
                  {m.content}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Composer */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur shadow-lg">
        <div className="flex items-start gap-3">
          <textarea
            value={composer}
            onChange={(e) => setComposer(e.target.value)}
            placeholder="메시지를 입력하세요"
            className="min-h-[64px] flex-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            onClick={handleSend}
            disabled={chatMutation.isPending}
            className="h-11 shrink-0 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white shadow-md transition hover:bg-blue-700 disabled:opacity-50"
          >
            {chatMutation.isPending ? "Sending..." : "Send"}
          </button>
        </div>

        {sendError && (
          <div className="mt-2 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {sendError}
          </div>
        )}
      </div>
    </div>
  </div>
);
}
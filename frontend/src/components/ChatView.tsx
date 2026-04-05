'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { Pencil, Trash2, Check, X } from 'lucide-react';

import { getModel, setModel } from '@/lib/modelStore';
import {
  addThreadBookmark,
  ChatMessage,
  getThread,
  listThreadBookmarks,
  postChat,
  removeThreadBookmark,
  ThreadBookmark,
} from '@/lib/threadApi';
import { getSupabaseToken } from '@/lib/apiFetch';
import { ThreadSearchBar } from './ThreadSearchBar';
import { supabase } from '@/lib/supabaseClient';
import { auth } from '@/lib/auth';
import { InlineLoginPrompt } from './InlineLoginPrompt';
import { WorkspaceCommentInput } from './WorkspaceCommentInput';

const MODEL_OPTIONS = ['gemma3:270m', 'llama3.1:8b', 'mistral:7b'];
const UUID_REGEX = /^[0-9a-fA-F-]{36}$/;

type BookmarkToggleVars = {
  messageIndex: number;
  nextBookmarked: boolean;
};

export function ChatView() {
  const params = useParams();
  const threadId = params?.threadId ? String(params.threadId) : '';
  const queryClient = useQueryClient();

  const [composer, setComposer] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pendingAssistantIndex, setPendingAssistantIndex] = useState<
    number | null
  >(null);
  const [sendError, setSendError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [matchIndex, setMatchIndex] = useState(0);
  const [matches, setMatches] = useState<number[]>([]);
  const [highlighted, setHighlighted] = useState<number | null>(null);

  const [selectedModel, setSelectedModel] = useState(() =>
    getModel(threadId, MODEL_OPTIONS[0]),
  );
  const [debugInfo, setDebugInfo] = useState<{
    url?: string;
    status?: number;
    bodySnippet?: string;
    hasToken?: boolean;
  }>({});

  const [token, setToken] = useState<string | null>(null);

  const [comments, setComments] = useState<Record<string, string[]>>({});
  const [commentAuthor, setCommentAuthor] = useState('me');
  const [commentNotice, setCommentNotice] = useState<string | null>(null);

  const [editingComment, setEditingComment] = useState<{
    targetId: string;
    index: number;
  } | null>(null);

  const [editingText, setEditingText] = useState('');

  const [bookmarkNotice, setBookmarkNotice] = useState<string | null>(null);
  const [isSummaryOpen, setIsSummaryOpen] = useState(false);

  useEffect(() => {
    let active = true;
    getSupabaseToken().then((t) => {
      if (active) setToken(t);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!active) return;
        const next = session?.access_token || null;
        if (next) {
          auth.setSession({
            accessToken: next,
            refreshToken: session?.refresh_token || undefined,
          });
        }
        setToken(next);
        const email = session?.user?.email || '';
        if (email) setCommentAuthor(email.split('@')[0]);
      },
    );

    supabase.auth.getSession().then(({ data }) => {
      const email = data.session?.user?.email || '';
      if (email) setCommentAuthor(email.split('@')[0]);
    });

    return () => {
      active = false;
      subscription?.subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = window.localStorage.getItem(`thread_comments_${threadId}`);
      if (raw) {
        const parsed = JSON.parse(raw);
        setComments(parsed || {});
      } else {
        setComments({});
      }
    } catch {
      setComments({});
    }
  }, [threadId]);

  const saveComments = (
    updater:
      | Record<string, string[]>
      | ((prev: Record<string, string[]>) => Record<string, string[]>),
  ) => {
    setComments((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      if (typeof window !== 'undefined') {
        try {
          window.localStorage.setItem(
            `thread_comments_${threadId}`,
            JSON.stringify(next),
          );
        } catch {}
      }
      return next;
    });
  };

  const resolveCommentTargetId = (message: ChatMessage, idx: number) => {
    if (message.id) return `id:${message.id}`;
    if (typeof message.index === 'number') return `index:${message.index}`;
    return `idx:${idx}`;
  };

  const resolveMessageIndex = (message: ChatMessage) => {
    if (typeof message.index === 'number' && Number.isFinite(message.index)) {
      return message.index;
    }
    return null;
  };

  const getMessageDomId = (message: ChatMessage, idx: number) => {
    const messageIndex = resolveMessageIndex(message);
    return messageIndex != null
      ? `msg-index-${messageIndex}`
      : `msg-idx-${idx}`;
  };

  const addComment = (targetId: string, text: string) => {
    const val = text.trim();
    if (!val) return;

    saveComments((prev) => {
      const next = { ...prev };
      const key = String(targetId);
      next[key] = [...(next[key] || []), `${commentAuthor}: ${val}`];
      return next;
    });

    setCommentNotice(
      'Comments are saved locally in this build (backend comments API is not wired).',
    );
    if (process.env.NODE_ENV !== 'production') {
      console.warn(
        '[comments] Saved locally; backend comments API is not connected.',
        {
          threadId,
          targetId,
        },
      );
    }
  };

  const deleteComment = (targetId: string, commentIndex: number) => {
    saveComments((prev) => {
      const next = { ...prev };
      const arr = [...(next[targetId] || [])];
      arr.splice(commentIndex, 1);

      if (arr.length === 0) {
        delete next[targetId];
      } else {
        next[targetId] = arr;
      }

      return next;
    });
  };

  const startEditComment = (targetId: string, index: number, text: string) => {
    setEditingComment({ targetId, index });

    // "username: 내용" → 내용만 추출
    const [, content] = text.split(': ');
    setEditingText(content || text);
  };

  const saveEditComment = () => {
    if (!editingComment) return;

    const { targetId, index } = editingComment;

    saveComments((prev) => {
      const next = { ...prev };
      const arr = [...(next[targetId] || [])];

      arr[index] = `${commentAuthor}: ${editingText}`;

      next[targetId] = arr;
      return next;
    });

    setEditingComment(null);
    setEditingText('');
  };

  const isValidThreadId = useMemo(() => UUID_REGEX.test(threadId), [threadId]);
  const isThreadScreen = !!threadId;

  const { data, isLoading, error } = useQuery({
    queryKey: ['thread', threadId],
    queryFn: () =>
      getThread(threadId, token!, (info) =>
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

  const isWorkspace = !!data?.is_workspace;

  const { data: bookmarkRows = [], error: bookmarkError } = useQuery<
    ThreadBookmark[]
  >({
    queryKey: ['thread-bookmarks', threadId],
    queryFn: () => listThreadBookmarks(threadId, token!),
    retry: false,
    enabled: isValidThreadId && !!token,
  });

  const bookmarkedIndexSet = useMemo(() => {
    return new Set((bookmarkRows || []).map((b) => b.message_index));
  }, [bookmarkRows]);

  useEffect(() => {
    setMessages([]);
    setMatches([]);
    setMatchIndex(0);
    setHighlighted(null);
  }, [threadId]);

  const chatMutation = useMutation({
    mutationFn: async (content: string) => {
      setSendError(null);
      if (!isValidThreadId) {
        throw Object.assign(new Error('Invalid thread id'), { status: 400 });
      }
      if (!token) {
        const err: any = new Error('NO_TOKEN');
        err.status = 401;
        err.code = 'NO_TOKEN';
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
      setMessages((prev) => {
        const updated = [...prev];
        if (pendingAssistantIndex != null && updated[pendingAssistantIndex]) {
          updated[pendingAssistantIndex] = {
            role: 'assistant',
            content: resp.assistant_content || '',
            created_at: new Date().toISOString(),
          };
        } else {
          updated.push({
            role: 'assistant',
            content: resp.assistant_content || '',
          });
        }
        return updated;
      });
      setPendingAssistantIndex(null);
      setComposer('');
      setDebugInfo((prev) => ({
        ...prev,
        status: 200,
        bodySnippet: resp?.assistant_content,
        hasToken: true,
      }));
      queryClient.invalidateQueries({ queryKey: ['thread', threadId] });
    },
    onError: (err: any) => {
      setPendingAssistantIndex(null);
      if (pendingAssistantIndex != null) {
        setMessages((prev) =>
          prev.filter((_, idx) => idx !== pendingAssistantIndex),
        );
      }
      const masked404 =
        err?.status === 404
          ? 'Thread not found or no access (masked 404). Check token and thread id.'
          : null;
      const invalidId =
        err?.message === 'Invalid thread id' ? err?.message : null;
      const noToken = err?.code === 'NO_TOKEN' ? 'Not logged in' : null;
      const message =
        noToken ||
        invalidId ||
        masked404 ||
        err?.message ||
        'Failed to send message.';
      setSendError(message);

      setDebugInfo((prev) => ({
        ...prev,
        status: err?.status,
        bodySnippet: err?.bodySnippet || err?.payload || err?.message,
      }));
      alert(message);
    },
  });

  const toggleBookmarkMutation = useMutation({
    mutationFn: async ({
      messageIndex,
      nextBookmarked,
    }: BookmarkToggleVars) => {
      if (!token) {
        const err: any = new Error('NO_TOKEN');
        err.code = 'NO_TOKEN';
        throw err;
      }
      if (nextBookmarked) {
        return addThreadBookmark(threadId, messageIndex, token);
      }
      return removeThreadBookmark(threadId, messageIndex, token);
    },
    onMutate: async ({ messageIndex, nextBookmarked }: BookmarkToggleVars) => {
      await queryClient.cancelQueries({
        queryKey: ['thread-bookmarks', threadId],
      });
      const previous =
        queryClient.getQueryData<ThreadBookmark[]>([
          'thread-bookmarks',
          threadId,
        ]) || [];
      queryClient.setQueryData<ThreadBookmark[]>(
        ['thread-bookmarks', threadId],
        (old) => {
          const base = old || [];
          if (nextBookmarked) {
            if (base.some((b) => b.message_index === messageIndex)) return base;
            return [
              ...base,
              { thread_id: threadId, message_index: messageIndex },
            ].sort((a, b) => a.message_index - b.message_index);
          }
          return base.filter((b) => b.message_index !== messageIndex);
        },
      );
      return { previous };
    },
    onError: (err: any, _vars: BookmarkToggleVars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          ['thread-bookmarks', threadId],
          context.previous,
        );
      }
      const reason =
        err?.bodySnippet || err?.message || 'Failed to update bookmark.';
      setBookmarkNotice(`Bookmark update failed: ${reason}`);
      if (process.env.NODE_ENV !== 'production') {
        console.warn('[bookmark] toggle failed', { threadId, reason });
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ['thread-bookmarks', threadId],
      });
    },
  });

  const handleSend = () => {
    if (!composer.trim()) return;
    const content = composer.trim();
    if (process.env.NODE_ENV !== 'production') {
      console.log('sending content', content, 'threadId', threadId);
    }

    const userMsg: ChatMessage = {
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    const assistantPlaceholder: ChatMessage = {
      role: 'assistant',
      content: 'Generating...',
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => {
      const next = [...prev, userMsg, assistantPlaceholder];
      setPendingAssistantIndex(next.length - 1);
      return next;
    });

    chatMutation.mutate(content);
  };

  const scrollToMatch = (idx: number) => {
    const message = messages[idx];
    if (!message) return;

    const el = document.getElementById(getMessageDomId(message, idx));
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setHighlighted(idx);
      setTimeout(() => setHighlighted(null), 1200);
    }
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

  const scrollToMessageIndex = (messageIndex: number) => {
    const msgPos = messages.findIndex((m) => m.index === messageIndex);
    if (msgPos < 0) return;
    scrollToMatch(msgPos);
  };

  const toggleBookmark = (message: ChatMessage) => {
    const messageIndex = resolveMessageIndex(message);
    if (messageIndex == null) {
      setBookmarkNotice(
        'This message is not ready to bookmark yet. Please try again in a moment.',
      );
      return;
    }
    setBookmarkNotice(null);
    const nextBookmarked = !bookmarkedIndexSet.has(messageIndex);
    toggleBookmarkMutation.mutate({ messageIndex, nextBookmarked });
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

  const title = data?.title || 'Thread';

  const summaryCards = useMemo(() => {
    const byIndex = new Map<number, ChatMessage>();
    messages.forEach((m) => {
      if (typeof m.index === 'number') {
        byIndex.set(m.index, m);
      }
    });

    return (bookmarkRows || [])
      .slice()
      .sort((a, b) => a.message_index - b.message_index)
      .map((b) => {
        const message = byIndex.get(b.message_index);
        return {
          messageIndex: b.message_index,
          role: message?.role || 'unknown',
          content: message?.content || '(message unavailable in current view)',
          createdAt: b.created_at,
        };
      });
  }, [bookmarkRows, messages]);

  useEffect(() => {
    if (!data?.messages) return;
    setMessages(
      data.messages.map((m, i) => ({
        ...m,
        index: m.index ?? i,
      })),
    );
  }, [data?.messages]);

  useEffect(() => {
    if (!commentNotice) return;
    const timer = setTimeout(() => setCommentNotice(null), 3000);
    return () => clearTimeout(timer);
  }, [commentNotice]);

  useEffect(() => {
    if (!bookmarkNotice) return;
    const timer = setTimeout(() => setBookmarkNotice(null), 3500);
    return () => clearTimeout(timer);
  }, [bookmarkNotice]);

  useEffect(() => {
    if (process.env.NODE_ENV === 'production') return;
    messages.forEach((m, idx) => {
      const commentTargetId = resolveCommentTargetId(m, idx);
      const isMessageBlock = typeof m?.content === 'string';
      const hasCommentTarget = !!commentTargetId;
      const showComment = isThreadScreen && isMessageBlock && hasCommentTarget;
      console.debug(
        showComment ? '[comments] renderable' : '[comments] blocked',
        {
          idx,
          threadId,
          role: m.role,
          isThreadScreen,
          isMessageBlock,
          hasCommentTarget,
          commentTargetId,
          isWorkspace,
        },
      );
    });
  }, [messages, threadId, isThreadScreen, isWorkspace]);

  if (!isValidThreadId) {
    return (
      <div className="flex h-full flex-col gap-2 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">
        <div className="font-semibold">Invalid thread id</div>
        <div className="text-sm">
          The provided thread id is not a valid UUID.
        </div>
        {process.env.NODE_ENV !== 'production' && (
          <div className="text-xs text-red-600">
            threadId: {threadId || '<empty>'}
          </div>
        )}
      </div>
    );
  }

  if (!token) {
    return (
      <InlineLoginPrompt
        title="Sign in to view this thread"
        message="Login to load messages and continue."
      />
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-slate-600">
        Loading thread...
      </div>
    );
  }

  if ((error as any)?.status === 401) {
    return (
      <InlineLoginPrompt
        title="Session expired"
        message="Please sign in again to view this thread."
      />
    );
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
        {(error as any)?.message || 'Failed to load thread'}
      </div>
    );
  }

  return (
    <div
      className={`fixed inset-0 overflow-hidden bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white ${
        isWorkspace ? 'bg-indigo-50 p-2 rounded-2xl' : ''
      }`}
    >
      <div className="mx-auto flex h-full max-w-6xl flex-col gap-4 p-6 md:p-10">
        <header className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-lg backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3 p-2">
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  if (typeof window !== 'undefined') {
                    window.location.href = '/threads';
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
                  {title || 'Untitled'}
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-white/60">
                Model
              </label>
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
              <button
                type="button"
                onClick={() => setIsSummaryOpen((prev) => !prev)}
                className="rounded-lg border border-white/15 bg-white/5 px-3 py-1 text-xs font-semibold text-white/80 transition hover:bg-white/10"
              >
                {isSummaryOpen ? 'Hide Summary Card' : 'Show Summary Card'} (
                {bookmarkRows.length})
              </button>
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

        <div
          className={`flex-1 min-h-0 ${isSummaryOpen ? 'grid grid-cols-1 gap-4 lg:grid-cols-4' : 'flex flex-col gap-4'}`}
        >
          <div
            className={`${isSummaryOpen ? 'lg:col-span-3 flex min-h-0 flex-col gap-4' : 'flex min-h-0 flex-1 flex-col gap-4'}`}
          >
            <div className="flex-1 overflow-y-auto rounded-2xl border border-white/10 bg-white/5 p-4 shadow-lg backdrop-blur">
              <div className="space-y-4">
                {messages.map((m, idx) => {
                  const commentTargetId = resolveCommentTargetId(m, idx);
                  const isMessageBlock = typeof m?.content === 'string';
                  const showCommentUI =
                    isThreadScreen && isMessageBlock && !!commentTargetId;
                  const messageComments = comments[commentTargetId] || [];
                  const messageIndex = resolveMessageIndex(m);
                  const isBookmarked =
                    messageIndex != null &&
                    bookmarkedIndexSet.has(messageIndex);
                  const domId = getMessageDomId(m, idx);

                  return (
                    <div
                      key={idx}
                      id={domId}
                      className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`relative max-w-[75%] rounded-2xl px-4 py-3 pr-10 text-sm shadow-md ${
                          m.role === 'user'
                            ? 'bg-blue-600 text-white'
                            : 'bg-white/10 text-white/90'
                        } ${highlighted === idx ? 'ring-2 ring-amber-400' : ''}`}
                      >
                        <button
                          type="button"
                          onClick={() => toggleBookmark(m)}
                          disabled={messageIndex == null}
                          aria-label={
                            isBookmarked ? 'Remove bookmark' : 'Add bookmark'
                          }
                          title={
                            messageIndex == null
                              ? 'Message is syncing; try again shortly'
                              : isBookmarked
                                ? 'Bookmarked'
                                : 'Bookmark'
                          }
                          className={`absolute right-2 top-2 rounded p-1 text-sm leading-none transition ${
                            isBookmarked
                              ? 'text-amber-300 hover:text-amber-200'
                              : 'text-white/60 hover:text-white'
                          } ${messageIndex == null ? 'cursor-not-allowed opacity-40' : ''}`}
                        >
                          {isBookmarked ? '★' : '☆'}
                        </button>

                        <div className="text-[11px] uppercase tracking-wide opacity-60">
                          {m.role}
                        </div>
                        <div className="mt-1 whitespace-pre-wrap leading-relaxed">
                          {m.content}
                        </div>

                        {showCommentUI && (
                          <div
                            className="mt-3 space-y-2"
                            data-comment-ui="true"
                            data-comment-target={commentTargetId}
                          >
                            {process.env.NODE_ENV !== 'production' && (
                              <div className="text-[10px] text-white/50">
                                comment-target: {commentTargetId}
                              </div>
                            )}
                            <div className="space-y-1">
                              {messageComments.map((c, ci) => {
                                const isEditing =
                                  editingComment?.targetId ===
                                    commentTargetId &&
                                  editingComment?.index === ci;

                                return (
                                  <div
                                    key={ci}
                                    className="rounded-lg bg-white/10 px-2 py-1 text-xs text-white/80"
                                  >
                                    {isEditing ? (
                                      <div className="flex items-center gap-1">
                                        <input
                                          value={editingText}
                                          onChange={(e) =>
                                            setEditingText(e.target.value)
                                          }
                                          className="flex-1 rounded bg-white/20 px-1 text-xs"
                                        />

                                        <button
                                          onClick={saveEditComment}
                                          className="text-green-300 hover:text-green-200"
                                        >
                                          <Check size={14} />
                                        </button>

                                        <button
                                          onClick={() =>
                                            setEditingComment(null)
                                          }
                                          className="text-red-300 hover:text-red-200"
                                        >
                                          <X size={14} />
                                        </button>
                                      </div>
                                    ) : (
                                      <div className="flex items-center justify-between gap-2">
                                        <span>{c}</span>

                                        <div className="flex gap-1">
                                          <button
                                            onClick={() =>
                                              startEditComment(
                                                commentTargetId,
                                                ci,
                                                c,
                                              )
                                            }
                                            className="text-blue-300 hover:text-blue-200"
                                          >
                                            <Pencil size={14} />
                                          </button>

                                          <button
                                            onClick={() =>
                                              deleteComment(commentTargetId, ci)
                                            }
                                            className="text-red-300 hover:text-red-200"
                                          >
                                            <Trash2 size={14} />
                                          </button>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>

                            <WorkspaceCommentInput
                              onAdd={(text) => {
                                addComment(commentTargetId, text);
                              }}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-lg backdrop-blur">
              <div className="flex items-start gap-3">
                <textarea
                  value={composer}
                  onChange={(e) => setComposer(e.target.value)}
                  placeholder="Type a message"
                  className="min-h-[64px] flex-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
                <button
                  onClick={handleSend}
                  disabled={chatMutation.isPending}
                  className="h-11 shrink-0 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white shadow-md transition hover:bg-blue-700 disabled:opacity-50"
                >
                  {chatMutation.isPending ? 'Sending...' : 'Send'}
                </button>
              </div>

              {commentNotice && (
                <div className="mt-2 rounded-lg bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
                  {commentNotice}
                </div>
              )}

              {bookmarkNotice && (
                <div className="mt-2 rounded-lg bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
                  {bookmarkNotice}
                </div>
              )}

              {sendError && (
                <div className="mt-2 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
                  {sendError}
                </div>
              )}
            </div>
          </div>

          {isSummaryOpen && (
            <aside className="min-h-0 lg:col-span-1">
              <div className="flex h-full min-h-0 flex-col rounded-2xl border border-white/10 bg-white/5 p-4 shadow-lg backdrop-blur">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-white/90">
                    Summary Card
                  </h2>
                  <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/80">
                    {summaryCards.length}
                  </span>
                </div>

                {bookmarkError && (
                  <div className="mb-3 rounded-lg border border-amber-300/30 bg-amber-300/10 px-2 py-1 text-xs text-amber-100">
                    Failed to load bookmarks:{' '}
                    {(bookmarkError as any)?.message || 'unknown error'}
                  </div>
                )}

                <div className="flex-1 space-y-2 overflow-y-auto pr-1">
                  {summaryCards.length === 0 ? (
                    <p className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-white/70">
                      북마크한 메시지가 아직 없습니다.
                    </p>
                  ) : (
                    summaryCards.map((card) => (
                      <div
                        key={card.messageIndex}
                        className="rounded-xl border border-white/10 bg-white/5 p-2"
                      >
                        <button
                          type="button"
                          onClick={() =>
                            scrollToMessageIndex(card.messageIndex)
                          }
                          className="w-full text-left"
                        >
                          <div className="text-[10px] font-semibold uppercase tracking-wide text-white/60">
                            {card.role} • #{card.messageIndex}
                          </div>
                          <div className="mt-1 line-clamp-5 whitespace-pre-wrap text-xs leading-relaxed text-white/90">
                            {card.content}
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            toggleBookmarkMutation.mutate({
                              messageIndex: card.messageIndex,
                              nextBookmarked: false,
                            })
                          }
                          className="mt-2 rounded-md bg-white/10 px-2 py-1 text-[11px] font-semibold text-white/80 transition hover:bg-white/20"
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

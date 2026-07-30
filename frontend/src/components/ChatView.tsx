'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import {
  Check,
  ChevronLeft,
  ChevronRight,
  GitBranch,
  Pencil,
  Trash2,
  X,
} from 'lucide-react';

import { getModel, setModel } from '@/lib/modelStore';
import { MODEL_OPTIONS } from '@/lib/models';
import {
  addThreadBookmark,
  ChatMessage,
  createThreadComment,
  createThreadBranch,
  deleteThreadComment,
  getThread,
  listThreadBookmarks,
  listThreadComments,
  postChat,
  removeThreadBookmark,
  ThreadBookmark,
  ThreadDetail,
  ThreadMessageComment,
  updateThreadComment,
  updateThreadTitle,
} from '@/lib/threadApi';
import { getSupabaseToken } from '@/lib/apiFetch';
import { ThreadSearchBar } from './ThreadSearchBar';
import { supabase } from '@/lib/supabaseClient';
import { auth } from '@/lib/auth';
import { InlineLoginPrompt } from './InlineLoginPrompt';
import { WorkspaceCommentInput } from './WorkspaceCommentInput';

const UUID_REGEX = /^[0-9a-fA-F-]{36}$/;
const SUMMARY_PREVIEW_MAX_CHARS = 800;

type BookmarkToggleVars = {
  messageIndex: number;
  nextBookmarked: boolean;
};

function ChatLoading({ label }: { label: string }) {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] px-4 text-white">
      <div
        role="status"
        aria-live="polite"
        className="rounded-2xl border border-white/10 bg-white/5 px-7 py-6 text-center shadow-2xl backdrop-blur"
      >
        <span
          aria-hidden="true"
          className="mx-auto block h-8 w-8 animate-spin rounded-full border-[3px] border-cyan-200/20 border-t-cyan-300 shadow-[0_0_18px_rgba(103,232,249,0.25)]"
        />
        <p className="mt-4 text-sm font-medium text-blue-100">{label}</p>
      </div>
    </div>
  );
}

export function ChatView() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
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

  useEffect(() => {
    if (!threadId) return;
    setSelectedModel(getModel(threadId, MODEL_OPTIONS[0]));
  }, [threadId]);
  const [, setDebugInfo] = useState<{
    url?: string;
    status?: number;
    bodySnippet?: string;
    hasToken?: boolean;
  }>({});

  const [token, setToken] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [commentNotice, setCommentNotice] = useState<string | null>(null);

  const [editingComment, setEditingComment] = useState<{
    targetId: string;
    commentId: string;
  } | null>(null);

  const [editingText, setEditingText] = useState('');

  const [bookmarkNotice, setBookmarkNotice] = useState<string | null>(null);
  const [branchError, setBranchError] = useState<string | null>(null);
  const [isSummaryOpen, setIsSummaryOpen] = useState(false);
  const [summaryCardIndex, setSummaryCardIndex] = useState(0);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [titleError, setTitleError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getSupabaseToken()
      .then((t) => {
        if (active) setToken(t);
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });

    const { data: subscription } = supabase
      ? supabase.auth.onAuthStateChange((_event, session) => {
          if (!active) return;
          const next = session?.access_token;
          // Hosted Google OAuth is persisted by the backend refresh cookie.
          // This browser client intentionally does not persist a Supabase
          // session, so its initial null event must not erase that session.
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
  }, []);

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

  const startEditComment = (
    targetId: string,
    comment: ThreadMessageComment,
  ) => {
    setEditingComment({ targetId, commentId: comment.id });

    // "username: 내용" → 내용만 추출
    setEditingText(comment.content);
  };

  const isValidThreadId = useMemo(() => UUID_REGEX.test(threadId), [threadId]);
  const isThreadScreen = !!threadId;

  const { data: commentRows = [] } = useQuery<ThreadMessageComment[]>({
    queryKey: ['thread-comments', threadId],
    queryFn: () => listThreadComments(threadId, token!),
    retry: false,
    enabled: isValidThreadId && !!token,
  });

  const comments = useMemo(() => {
    const grouped: Record<string, ThreadMessageComment[]> = {};
    commentRows.forEach((comment) => {
      const key = `index:${comment.message_index}`;
      grouped[key] = [...(grouped[key] || []), comment];
    });
    return grouped;
  }, [commentRows]);

  const refreshComments = () =>
    queryClient.invalidateQueries({
      queryKey: ['thread-comments', threadId],
    });

  const addComment = async (messageIndex: number, text: string) => {
    const content = text.trim();
    if (!content || !token) return;
    try {
      await createThreadComment(threadId, messageIndex, content, token);
      await refreshComments();
      setCommentNotice('코멘트가 저장되었습니다.');
    } catch (commentError) {
      setCommentNotice(
        commentError instanceof Error
          ? commentError.message
          : '코멘트를 저장하지 못했습니다.',
      );
    }
  };

  const deleteComment = async (comment: ThreadMessageComment) => {
    if (!token || !comment.can_edit) return;
    try {
      await deleteThreadComment(threadId, comment.id, token);
      await refreshComments();
      setCommentNotice('코멘트가 삭제되었습니다.');
    } catch (commentError) {
      setCommentNotice(
        commentError instanceof Error
          ? commentError.message
          : '코멘트를 삭제하지 못했습니다.',
      );
    }
  };

  const saveEditComment = async () => {
    if (!editingComment || !token || !editingText.trim()) return;
    try {
      await updateThreadComment(
        threadId,
        editingComment.commentId,
        editingText.trim(),
        token,
      );
      await refreshComments();
      setEditingComment(null);
      setEditingText('');
      setCommentNotice('코멘트가 수정되었습니다.');
    } catch (commentError) {
      setCommentNotice(
        commentError instanceof Error
          ? commentError.message
          : '코멘트를 수정하지 못했습니다.',
      );
    }
  };

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
  const returnSource = searchParams.get('from');
  const returnRootId = searchParams.get('root');
  const isBranchZipReturn = returnSource === 'branch-zip';
  const backHref = isBranchZipReturn
    ? `/branch-zip${returnRootId ? `?root=${encodeURIComponent(returnRootId)}` : ''}`
    : data?.root_thread_id
      ? `/thread-folders/${data.root_thread_id}`
      : '/threads';

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

  const branchMutation = useMutation({
    mutationFn: async () => {
      setBranchError(null);
      if (!token) {
        const err: any = new Error('NO_TOKEN');
        err.code = 'NO_TOKEN';
        throw err;
      }
      return createThreadBranch(threadId, selectedModel, token);
    },
    onSuccess: (branch) => {
      setModel(branch.thread_id, selectedModel);
      queryClient.invalidateQueries({ queryKey: ['threads'] });
      queryClient.invalidateQueries({ queryKey: ['thread-branches'] });
      router.push(`/threads/${branch.thread_id}`);
    },
    onError: (err: any) => {
      const message =
        err?.code === 'NO_TOKEN'
          ? '로그인이 필요합니다.'
          : err?.message || '브랜치를 만들지 못했습니다.';
      setBranchError(message);
    },
  });

  const titleMutation = useMutation({
    mutationFn: async (nextTitle: string) => {
      if (!token) {
        throw new Error('로그인이 필요합니다.');
      }
      return updateThreadTitle(threadId, nextTitle, token);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<ThreadDetail>(
        ['thread', threadId],
        (current) =>
          current ? { ...current, title: updated.title } : current,
      );
      void queryClient.invalidateQueries({ queryKey: ['threads'] });
      void queryClient.invalidateQueries({ queryKey: ['thread-branches'] });
      setIsEditingTitle(false);
      setTitleDraft('');
      setTitleError(null);
    },
    onError: (error: Error) => {
      setTitleError(error.message || '스레드명을 수정하지 못했습니다.');
    },
  });

  const saveTitle = () => {
    const normalized = titleDraft.trim();
    if (!normalized) {
      setTitleError('스레드명을 입력하세요.');
      return;
    }
    titleMutation.mutate(normalized);
  };

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
  const isGeminiSelected = selectedModel.toLowerCase().startsWith('gemini');
  const branchContextPreview = data?.context_preview
    ? Array.from(data.context_preview).slice(0, 20).join('')
    : '';

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
          content: (() => {
            const content =
              message?.content || '(message unavailable in current view)';
            const characters = Array.from(content);
            return characters.length > SUMMARY_PREVIEW_MAX_CHARS
              ? `${characters
                  .slice(0, SUMMARY_PREVIEW_MAX_CHARS)
                  .join('')}…`
              : content;
          })(),
          createdAt: b.created_at,
        };
      });
  }, [bookmarkRows, messages]);

  const activeSummaryCard = summaryCards[summaryCardIndex] || null;

  useEffect(() => {
    setSummaryCardIndex((current) =>
      summaryCards.length === 0
        ? 0
        : Math.min(current, summaryCards.length - 1),
    );
  }, [summaryCards.length]);

  useEffect(() => {
    setSummaryCardIndex(0);
  }, [threadId]);

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

  if (!isValidThreadId) {
    return (
      <div className="flex h-full flex-col gap-2 rounded-2xl border border-rose-300/25 bg-rose-500/10 p-4 text-rose-100">
        <div className="font-semibold">잘못된 스레드 주소입니다</div>
        <div className="text-sm">
          스레드 식별자 형식이 올바르지 않습니다.
        </div>
        {process.env.NODE_ENV !== 'production' && (
          <div className="text-xs text-red-600">
            threadId: {threadId || '<empty>'}
          </div>
        )}
      </div>
    );
  }

  if (authLoading) {
    return <ChatLoading label="로그인 상태를 확인하는 중입니다..." />;
  }

  if (!token) {
    return (
      <InlineLoginPrompt
        title="스레드를 열려면 로그인하세요"
        message="로그인하면 저장된 메시지를 불러와 대화를 이어갈 수 있습니다."
      />
    );
  }

  if (isLoading) {
    return <ChatLoading label="스레드를 불러오는 중입니다..." />;
  }

  if ((error as any)?.status === 401) {
    return (
      <InlineLoginPrompt
        title="로그인 세션이 만료되었습니다"
        message="이 스레드를 보려면 다시 로그인해 주세요."
      />
    );
  }

  if ((error as any)?.status === 404) {
    return (
      <div className="flex h-full items-center justify-center text-blue-100">
        스레드가 없거나 접근 권한이 없습니다.
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center text-rose-300">
        {(error as any)?.message || '스레드를 불러오지 못했습니다.'}
      </div>
    );
  }

  return (
    <div
      className={`fixed inset-0 min-w-0 overflow-hidden bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white ${
        isWorkspace ? 'ring-1 ring-inset ring-indigo-300/15' : ''
      }`}
    >
      <div className="mx-auto flex h-[100dvh] max-w-6xl flex-col gap-2 p-2 pb-[max(.5rem,env(safe-area-inset-bottom))] pt-[max(.5rem,env(safe-area-inset-top))] sm:gap-4 sm:p-4 md:p-10">
        <header className="shrink-0 rounded-2xl border border-white/10 bg-white/5 p-2 shadow-lg backdrop-blur sm:p-4">
          <div className="flex flex-wrap items-start justify-between gap-3 p-1 sm:items-center sm:p-2">
            <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
              <button
                onClick={() => router.push(backHref)}
                aria-label={
                  isBranchZipReturn
                    ? '브랜치 시각화로 돌아가기'
                    : data?.root_thread_id
                    ? '브랜치 폴더로 돌아가기'
                    : '스레드 목록으로 돌아가기'
                }
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sm font-semibold text-white/80 hover:bg-white/10"
              >
                ←
              </button>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/50">
                  Thread
                </p>
                {isEditingTitle ? (
                  <div className="mt-1">
                    <div className="flex items-center gap-1.5">
                      <input
                        autoFocus
                        value={titleDraft}
                        maxLength={200}
                        disabled={titleMutation.isPending}
                        onChange={(event) => setTitleDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') {
                            event.preventDefault();
                            saveTitle();
                          } else if (event.key === 'Escape') {
                            setIsEditingTitle(false);
                            setTitleError(null);
                          }
                        }}
                        aria-label="스레드명 수정"
                        className="w-full min-w-0 max-w-64 rounded-lg border border-cyan-300/30 bg-white/5 px-2.5 py-1 text-base font-bold text-white outline-none focus:ring-2 focus:ring-cyan-300/40"
                      />
                      <button
                        type="button"
                        onClick={saveTitle}
                        disabled={titleMutation.isPending}
                        aria-label="스레드명 저장"
                        className="rounded-md p-1.5 text-emerald-300 transition hover:bg-emerald-300/10 disabled:opacity-50"
                      >
                        {titleMutation.isPending ? (
                          <span className="block h-4 w-4 animate-spin rounded-full border-2 border-emerald-300 border-t-transparent" />
                        ) : (
                          <Check size={16} />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setIsEditingTitle(false);
                          setTitleError(null);
                        }}
                        disabled={titleMutation.isPending}
                        aria-label="스레드명 수정 취소"
                        className="rounded-md p-1.5 text-white/45 transition hover:bg-white/10 disabled:opacity-50"
                      >
                        <X size={16} />
                      </button>
                    </div>
                    {titleError && (
                      <p className="mt-1 text-xs text-rose-300">{titleError}</p>
                    )}
                  </div>
                ) : (
                  <div className="flex min-w-0 items-center gap-2">
                    <h1 className="max-w-[58vw] truncate text-base font-bold text-white/90 sm:max-w-md sm:text-xl">
                      {title || 'Untitled'}
                    </h1>
                    {data?.can_rename && (
                      <button
                        type="button"
                        onClick={() => {
                          setTitleDraft(title || '');
                          setTitleError(null);
                          setIsEditingTitle(true);
                        }}
                        aria-label="스레드명 수정"
                        title="스레드명 수정"
                        className="shrink-0 rounded-md p-1.5 text-white/40 transition hover:bg-cyan-300/10 hover:text-cyan-200"
                      >
                        <Pencil size={15} />
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
              <label className="hidden text-xs font-semibold text-white sm:block">
                Model
              </label>
              <select
                value={selectedModel}
                onChange={(e) => {
                  setSelectedModel(e.target.value);
                  setModel(threadId, e.target.value);
                }}
                className="min-h-10 min-w-0 flex-1 rounded-lg border border-white/10 bg-slate-900/80 px-2 py-1 text-sm text-white focus:outline-none sm:flex-none"
              >
                {MODEL_OPTIONS.map((m) => (
                  <option
                    key={m}
                    value={m}
                    className="bg-slate-900 text-white"
                  >
                    {m}
                  </option>
                ))}
              </select>
              {selectedModel === 'gemini-2.5-flash' && (
                <span className="hidden text-[10px] text-white/75 sm:inline">
                  최신 Flash 호환 실행
                </span>
              )}
              <button
                type="button"
                onClick={() => setIsSummaryOpen((prev) => !prev)}
                className="min-h-10 flex-1 rounded-lg border border-white/15 bg-white/5 px-3 py-1 text-xs font-semibold text-white/80 transition hover:bg-white/10 sm:flex-none"
              >
                {isSummaryOpen ? '요약 닫기' : '요약 카드'} ({bookmarkRows.length})
              </button>
            </div>
          </div>

          {isGeminiSelected && (
            <div className="mb-3 flex flex-wrap items-center justify-end gap-3 border-t border-white/10 pt-3">
              {branchError && (
                <p role="alert" className="text-xs text-rose-300">
                  {branchError}
                </p>
              )}
              <button
                type="button"
                onClick={() => branchMutation.mutate()}
                disabled={branchMutation.isPending || chatMutation.isPending}
                className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-400/10 px-4 py-2 text-sm font-semibold text-cyan-100 transition hover:border-cyan-200/60 hover:bg-cyan-400/20 disabled:cursor-wait disabled:opacity-60 sm:w-auto"
              >
                <GitBranch
                  size={16}
                  className={branchMutation.isPending ? 'animate-pulse' : ''}
                />
                {branchMutation.isPending ? '브랜치 생성 중...' : '브랜치'}
              </button>
            </div>
          )}

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
          className={`relative min-h-0 flex-1 ${isSummaryOpen ? 'flex flex-col gap-2 lg:grid lg:grid-cols-4 lg:gap-4' : 'flex flex-col gap-2 sm:gap-4'}`}
        >
          <div
            className={`${isSummaryOpen ? 'flex min-h-0 flex-1 flex-col gap-2 lg:col-span-3 lg:gap-4' : 'flex min-h-0 flex-1 flex-col gap-2 sm:gap-4'}`}
          >
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain rounded-2xl border border-white/10 bg-white/5 p-3 shadow-lg backdrop-blur sm:p-4">
              <div className="space-y-4">
                {branchContextPreview && (
                  <div
                    role="status"
                    className="sticky top-0 z-10 mx-auto w-fit max-w-full rounded-full border border-cyan-300/30 bg-slate-950/90 px-4 py-2 text-center text-xs font-semibold text-cyan-100 shadow-lg backdrop-blur"
                  >
                    이전 Gemini 컨텍스트 · {branchContextPreview}
                  </div>
                )}
                {messages.map((m, idx) => {
                  const commentTargetId = resolveCommentTargetId(m, idx);
                  const isMessageBlock = typeof m?.content === 'string';
                  const messageIndex = resolveMessageIndex(m);
                  const showCommentUI =
                    isWorkspace &&
                    isThreadScreen &&
                    isMessageBlock &&
                    m.role === 'assistant' &&
                    !!commentTargetId &&
                    messageIndex != null;
                  const messageComments = comments[commentTargetId] || [];
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
                        className={`relative max-w-[92%] overflow-hidden rounded-2xl px-3 py-3 pr-9 text-sm shadow-md sm:max-w-[75%] sm:px-4 sm:pr-10 ${
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
                        <div className="mt-1 whitespace-pre-wrap break-words leading-relaxed">
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
                              {messageComments.map((comment) => {
                                const isEditing =
                                  editingComment?.targetId ===
                                    commentTargetId &&
                                  editingComment?.commentId === comment.id;

                                return (
                                  <div
                                    key={comment.id}
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
                                          onClick={() =>
                                            void saveEditComment()
                                          }
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
                                        <span className="min-w-0 break-words">
                                          <strong className="mr-1 text-cyan-200">
                                            {comment.author_id || '사용자'}:
                                          </strong>
                                          {comment.content}
                                        </span>

                                        {comment.can_edit && (
                                          <div className="flex shrink-0 gap-1">
                                            <button
                                              onClick={() =>
                                                startEditComment(
                                                  commentTargetId,
                                                  comment,
                                                )
                                              }
                                              className="text-blue-300 hover:text-blue-200"
                                            >
                                              <Pencil size={14} />
                                            </button>

                                            <button
                                              onClick={() =>
                                                void deleteComment(comment)
                                              }
                                              className="text-red-300 hover:text-red-200"
                                            >
                                              <Trash2 size={14} />
                                            </button>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>

                            <WorkspaceCommentInput
                              onAdd={(text) => {
                                if (messageIndex != null) {
                                  void addComment(messageIndex, text);
                                }
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

            <div className="shrink-0 rounded-2xl border border-white/10 bg-white/5 p-3 shadow-lg backdrop-blur sm:p-4">
              <div className="flex items-end gap-2 sm:items-start sm:gap-3">
                <textarea
                  value={composer}
                  onChange={(e) => setComposer(e.target.value)}
                  placeholder="Type a message"
                  className="min-h-[56px] min-w-0 flex-1 resize-none rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400 sm:min-h-[64px]"
                />
                <div className="relative shrink-0 overflow-hidden rounded-xl p-[2px]">
                  {chatMutation.isPending && (
                    <span
                      aria-hidden="true"
                      className="absolute inset-[-150%] animate-[spin_1.15s_linear_infinite] bg-[conic-gradient(from_0deg,transparent_0deg,transparent_255deg,#67e8f9_300deg,#ffffff_330deg,transparent_360deg)]"
                    />
                  )}
                  <button
                    onClick={handleSend}
                    disabled={chatMutation.isPending}
                    className="relative z-10 h-12 rounded-[10px] bg-blue-600 px-3 text-sm font-semibold text-white shadow-md transition hover:bg-blue-700 disabled:cursor-wait sm:px-4"
                  >
                    {chatMutation.isPending ? 'Sending...' : 'Send'}
                  </button>
                </div>
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
            <aside className="absolute inset-0 z-40 min-h-0 lg:static lg:col-span-1">
              <div
                className="flex h-full min-h-0 flex-col rounded-2xl border border-white/15 bg-slate-950/95 p-3 shadow-2xl backdrop-blur sm:p-4 lg:bg-white/5 lg:shadow-lg"
                aria-label="요약 카드 캐러셀"
                aria-roledescription="carousel"
                onKeyDown={(event) => {
                  if (event.key === 'ArrowLeft' && summaryCardIndex > 0) {
                    event.preventDefault();
                    setSummaryCardIndex((current) => current - 1);
                  } else if (
                    event.key === 'ArrowRight' &&
                    summaryCardIndex < summaryCards.length - 1
                  ) {
                    event.preventDefault();
                    setSummaryCardIndex((current) => current + 1);
                  }
                }}
              >
                <div className="mb-3 flex min-h-11 shrink-0 items-center justify-between gap-2">
                  <div className="min-w-0">
                    <h2 className="text-sm font-semibold text-white">
                      요약 카드
                    </h2>
                    <p className="mt-0.5 text-[10px] text-white/50">
                      북마크한 메시지 미리보기
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span
                      className="min-w-12 rounded-full bg-white/10 px-2 py-1 text-center text-xs font-semibold text-white/80"
                      aria-live="polite"
                    >
                      {summaryCards.length === 0
                        ? '0 / 0'
                        : `${summaryCardIndex + 1} / ${summaryCards.length}`}
                    </span>
                    <button
                      type="button"
                      onClick={() => setIsSummaryOpen(false)}
                      aria-label="요약 카드 닫기"
                      className="flex h-11 w-11 items-center justify-center rounded-xl text-white/65 transition hover:bg-white/10 hover:text-white lg:hidden"
                    >
                      <X size={18} />
                    </button>
                  </div>
                </div>

                {bookmarkError && (
                  <div className="mb-3 shrink-0 rounded-lg border border-amber-300/30 bg-amber-300/10 px-3 py-2 text-xs text-amber-100">
                    북마크를 불러오지 못했습니다:{' '}
                    {(bookmarkError as any)?.message || '알 수 없는 오류'}
                  </div>
                )}

                <div className="flex min-h-0 flex-1 flex-col items-center justify-center">
                  {activeSummaryCard ? (
                    <article
                      key={activeSummaryCard.messageIndex}
                      className="flex h-[20rem] w-full max-w-md shrink-0 flex-col overflow-hidden rounded-2xl border border-cyan-200/20 bg-gradient-to-br from-white/10 via-cyan-200/[0.06] to-indigo-300/[0.08] p-3 shadow-xl shadow-cyan-950/20 sm:h-[22rem] sm:p-4 lg:h-[24rem] lg:max-w-none"
                      aria-label={`요약 카드 ${summaryCardIndex + 1}`}
                    >
                      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-white/10 pb-3">
                        <div className="min-w-0">
                          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-cyan-100/65">
                            {activeSummaryCard.role}
                          </p>
                          <p className="mt-1 text-xs font-semibold text-white/85">
                            메시지 #{activeSummaryCard.messageIndex}
                          </p>
                        </div>
                        <span className="rounded-full border border-cyan-200/15 bg-cyan-200/10 px-2.5 py-1 text-[10px] font-semibold text-cyan-50/80">
                          Preview
                        </span>
                      </div>

                      <div className="my-3 min-h-0 flex-1 overflow-y-auto overscroll-contain rounded-xl border border-white/10 bg-slate-950/30 px-3 py-3 [scrollbar-color:rgba(103,232,249,0.35)_rgba(15,23,42,0.35)] [scrollbar-width:thin]">
                        <p className="whitespace-pre-wrap break-words text-sm leading-6 text-white/90">
                          {activeSummaryCard.content}
                        </p>
                      </div>

                      <div className="grid shrink-0 grid-cols-2 gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            scrollToMessageIndex(
                              activeSummaryCard.messageIndex,
                            )
                          }
                          className="min-h-11 rounded-xl border border-cyan-200/20 bg-cyan-300/10 px-2 py-2 text-xs font-bold text-cyan-50 transition hover:bg-cyan-300/20"
                        >
                          대화에서 보기
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            toggleBookmarkMutation.mutate({
                              messageIndex: activeSummaryCard.messageIndex,
                              nextBookmarked: false,
                            })
                          }
                          disabled={toggleBookmarkMutation.isPending}
                          className="min-h-11 rounded-xl border border-white/10 bg-white/5 px-2 py-2 text-xs font-semibold text-white/75 transition hover:bg-white/10 hover:text-white disabled:cursor-wait disabled:opacity-45"
                        >
                          요약에서 제거
                        </button>
                      </div>
                    </article>
                  ) : (
                    <div className="flex h-[20rem] w-full max-w-md items-center justify-center rounded-2xl border border-dashed border-white/15 bg-white/[0.04] px-6 text-center sm:h-[22rem] lg:h-[24rem] lg:max-w-none">
                      <div>
                        <p className="text-sm font-semibold text-white/80">
                          북마크한 메시지가 없습니다.
                        </p>
                        <p className="mt-2 text-xs leading-5 text-white/50">
                          대화 메시지의 별표 버튼을 누르면 이곳에서 요약
                          카드로 확인할 수 있습니다.
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-3 grid shrink-0 grid-cols-[2.75rem_minmax(0,1fr)_2.75rem] items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      setSummaryCardIndex((current) => current - 1)
                    }
                    disabled={summaryCardIndex <= 0}
                    aria-label="이전 요약 카드"
                    className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white transition hover:border-cyan-200/25 hover:bg-cyan-300/10 disabled:cursor-not-allowed disabled:opacity-25"
                  >
                    <ChevronLeft size={20} />
                  </button>
                  <div className="flex items-center justify-center gap-1.5 overflow-hidden">
                    {summaryCards.map((card, index) => (
                      <button
                        key={card.messageIndex}
                        type="button"
                        onClick={() => setSummaryCardIndex(index)}
                        aria-label={`${index + 1}번 요약 카드로 이동`}
                        aria-current={
                          index === summaryCardIndex ? 'true' : undefined
                        }
                        className={`h-2 rounded-full transition-all ${
                          index === summaryCardIndex
                            ? 'w-6 bg-cyan-300'
                            : 'w-2 bg-white/25 hover:bg-white/45'
                        }`}
                      />
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setSummaryCardIndex((current) => current + 1)
                    }
                    disabled={
                      summaryCards.length === 0 ||
                      summaryCardIndex >= summaryCards.length - 1
                    }
                    aria-label="다음 요약 카드"
                    className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white transition hover:border-cyan-200/25 hover:bg-cyan-300/10 disabled:cursor-not-allowed disabled:opacity-25"
                  >
                    <ChevronRight size={20} />
                  </button>
                </div>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

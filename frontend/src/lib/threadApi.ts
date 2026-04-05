import { apiFetch, FetchDebug } from "./apiFetch";

export type ThreadSummary = {
  id: string;
  title: string | null;
  created_at: string;
  is_workspace?: boolean;
  message_count?: number;
  last_message_preview?: string | null;
};

export type ChatMessage = {
  id?: string;
  index?: number;
  role: "user" | "assistant" | "system" | string;
  content: string;
  created_at?: string;
};

export type ThreadDetail = {
  id: string;
  title: string | null;
  created_at: string;
  messages: ChatMessage[];
  is_workspace?: boolean;
};

export type ChatRequest = {
  content: string;
  model: string;
  context_limit: number;
};

export type ChatResponse = {
  thread_id: string;
  user_content: string;
  assistant_content: string;
  assistant_index: number;
  status: string;
};

export type ThreadBookmark = {
  thread_id: string;
  message_index: number;
  created_at?: string;
};

export async function listThreads(
  params: { limit?: number; offset?: number; order?: "asc" | "desc" } = {},
  token: string,
  onDebug?: (info: FetchDebug) => void,
) {
  const search = new URLSearchParams();
  if (params.limit) search.set("limit", String(params.limit));
  if (params.offset) search.set("offset", String(params.offset));
  if (params.order) search.set("order", params.order);
  const query = search.toString();
  const data = await apiFetch(`/threads${query ? `?${query}` : ""}`, { method: "GET" }, token, onDebug);
  return Array.isArray(data) ? data : data?.threads || [];
}

export async function createThread(body: { title: string; messages: ChatMessage[] }, token: string, onDebug?: (info: FetchDebug) => void) {
  return apiFetch(
    "/threads",
    {
      method: "POST",
      body,
    },
    token,
    onDebug,
  );
}

export async function getThread(threadId: string, token: string, onDebug?: (info: FetchDebug) => void): Promise<ThreadDetail> {
  return apiFetch(`/threads/${threadId}`, { method: "GET" }, token, onDebug);
}

export async function deleteThread(threadId: string, token: string, onDebug?: (info: FetchDebug) => void) {
  return apiFetch(`/threads/${threadId}`, { method: "DELETE" }, token, onDebug);
}

export async function createWorkspace(threadId: string, emails: string[], token?: string, onDebug?: (info: FetchDebug) => void) {
  return apiFetch(
    `/threads/${threadId}/workspace`,
    {
      method: "POST",
      body: { emails },
    },
    token || undefined,
    onDebug,
  );
}

export async function fetchMembers(threadId: string, token?: string, onDebug?: (info: FetchDebug) => void) {
  return apiFetch(`/threads/${threadId}/members`, { method: "GET" }, token || undefined, onDebug);
}

export async function postChat(
  threadId: string,
  payload: ChatRequest,
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<ChatResponse> {
  if (!threadId) {
    throw new Error("Thread ID is missing. Cannot call chat endpoint.");
  }
  const url = `/threads/${threadId}/chat`;
  return apiFetch(
    url,
    {
      method: "POST",
      body: payload,
    },
    token,
    onDebug,
  );
}

export async function setWorkspace(
  threadId: string,
  token: string,
  onDebug?: (info: FetchDebug) => void,
) {
  return apiFetch(
    `/threads/${threadId}/workspace`,
    {
      method: "PATCH",
      body: {
        is_workspace: true,
      },
    },
    token,
    onDebug,
  );
}

export async function listThreadBookmarks(threadId: string, token: string, onDebug?: (info: FetchDebug) => void): Promise<ThreadBookmark[]> {
  const data = await apiFetch(`/threads/${threadId}/bookmarks`, { method: "GET" }, token, onDebug);
  return Array.isArray(data) ? data : data?.bookmarks || [];
}

export async function addThreadBookmark(
  threadId: string,
  messageIndex: number,
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<ThreadBookmark> {
  return apiFetch(
    `/threads/${threadId}/bookmarks`,
    {
      method: "POST",
      body: { message_index: messageIndex },
    },
    token,
    onDebug,
  );
}

export async function removeThreadBookmark(
  threadId: string,
  messageIndex: number,
  token: string,
  onDebug?: (info: FetchDebug) => void,
) {
  return apiFetch(`/threads/${threadId}/bookmarks/${messageIndex}`, { method: "DELETE" }, token, onDebug);
}

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
  role: "user" | "assistant" | "system" | string;
  content: string;
  created_at?: string;
};

export type ThreadDetail = {
  id: string;
  title: string | null;
  created_at: string;
  messages: ChatMessage[];
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

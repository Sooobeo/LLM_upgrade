import { apiFetch, FetchDebug } from "./apiFetch";

export type ThreadSummary = {
  id: string;
  title: string | null;
  created_at: string;
  is_workspace?: boolean;
  workspace_role?: string | null;
  can_manage_workspace?: boolean;
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
  workspace_role?: string | null;
  can_manage_workspace?: boolean;
  can_rename?: boolean;
  parent_thread_id?: string | null;
  context_preview?: string | null;
};

export type BranchCreateResponse = {
  thread_id: string;
  title: string;
  parent_thread_id: string;
  context_preview: string;
  status: string;
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

export type ThreadMessageComment = {
  id: string;
  thread_id: string;
  message_index: number;
  user_id: string;
  author_id?: string | null;
  can_edit?: boolean;
  content: string;
  created_at?: string | null;
};

export type BranchNode = {
  id: string;
  title: string;
  parent_thread_id?: string | null;
  context_preview?: string;
  created_at?: string;
  is_deleted?: boolean;
  is_tutorial?: boolean;
  can_manage?: boolean;
  is_workspace?: boolean;
  workspace_role?: string | null;
  can_manage_workspace?: boolean;
  children: BranchNode[];
};

export type BranchNodeComment = {
  id: string;
  thread_id: string;
  user_id: string;
  author_id: string;
  can_edit: boolean;
  content: string;
  position_x: number;
  position_y: number;
  created_at?: string | null;
};

export type FlatBranchNode = BranchNode & {
  depth: number;
};

export function flattenBranchTree(
  root: BranchNode,
  depth = 0,
): FlatBranchNode[] {
  return [
    { ...root, depth },
    ...(root.children || []).flatMap((child) =>
      flattenBranchTree(child, depth + 1),
    ),
  ];
}

export function collectBranchThreadIds(roots: BranchNode[]): Set<string> {
  return new Set(
    roots.flatMap((root) => flattenBranchTree(root).map((node) => node.id)),
  );
}

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

export async function listThreadBranches(
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<{ roots: BranchNode[] }> {
  const data = await apiFetch("/threads/branches", { method: "GET" }, token, onDebug);
  return {
    roots: Array.isArray(data) ? data : Array.isArray(data?.roots) ? data.roots : [],
  };
}

export async function listBranchNodeComments(
  threadIds: string[],
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<BranchNodeComment[]> {
  const search = new URLSearchParams();
  threadIds.forEach((threadId) => search.append("thread_id", threadId));
  const data = await apiFetch(
    `/branch-comments?${search.toString()}`,
    { method: "GET" },
    token,
    onDebug,
  );
  return Array.isArray(data) ? data : [];
}

export async function createBranchNodeComment(
  payload: {
    thread_id: string;
    content: string;
    position_x: number;
    position_y: number;
  },
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<BranchNodeComment> {
  return apiFetch(
    "/branch-comments",
    { method: "POST", body: payload },
    token,
    onDebug,
  );
}

export async function updateBranchNodeComment(
  commentId: string,
  payload: {
    content?: string;
    position_x?: number;
    position_y?: number;
  },
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<BranchNodeComment> {
  return apiFetch(
    `/branch-comments/${commentId}`,
    { method: "PATCH", body: payload },
    token,
    onDebug,
  );
}

export async function deleteBranchNodeComment(
  commentId: string,
  token: string,
  onDebug?: (info: FetchDebug) => void,
) {
  return apiFetch(
    `/branch-comments/${commentId}`,
    { method: "DELETE" },
    token,
    onDebug,
  );
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

export async function createThreadBranch(
  threadId: string,
  model: string,
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<BranchCreateResponse> {
  return apiFetch(
    `/threads/${threadId}/branch`,
    {
      method: "POST",
      body: { model },
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

export async function updateThreadTitle(
  threadId: string,
  title: string,
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<{ thread_id: string; title: string; status: string }> {
  return apiFetch(
    `/threads/${threadId}`,
    {
      method: "PATCH",
      body: { title },
    },
    token,
    onDebug,
  );
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

export async function listThreadComments(
  threadId: string,
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<ThreadMessageComment[]> {
  const data = await apiFetch(
    `/threads/${threadId}/comments`,
    { method: "GET" },
    token,
    onDebug,
  );
  return Array.isArray(data) ? data : [];
}

export async function createThreadComment(
  threadId: string,
  messageIndex: number,
  content: string,
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<ThreadMessageComment> {
  return apiFetch(
    `/threads/${threadId}/comments`,
    {
      method: "POST",
      body: { message_index: messageIndex, content },
    },
    token,
    onDebug,
  );
}

export async function updateThreadComment(
  threadId: string,
  commentId: string,
  content: string,
  token: string,
  onDebug?: (info: FetchDebug) => void,
): Promise<ThreadMessageComment> {
  return apiFetch(
    `/threads/${threadId}/comments/${commentId}`,
    { method: "PATCH", body: { content } },
    token,
    onDebug,
  );
}

export async function deleteThreadComment(
  threadId: string,
  commentId: string,
  token: string,
  onDebug?: (info: FetchDebug) => void,
) {
  return apiFetch(
    `/threads/${threadId}/comments/${commentId}`,
    { method: "DELETE" },
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

const STORAGE_KEY = "thread-model-selection";

type ModelMap = Record<string, string>;

function readMap(): ModelMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ModelMap) : {};
  } catch {
    return {};
  }
}

export function getModel(threadId: string, fallback: string) {
  const map = readMap();
  return map[threadId] || fallback;
}

export function setModel(threadId: string, model: string) {
  if (typeof window === "undefined") return;
  const map = readMap();
  map[threadId] = model;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // ignore storage errors
  }
}

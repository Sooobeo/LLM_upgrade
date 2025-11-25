const STORAGE_KEY = "access_token";

function getStorage() {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export const auth = {
  getToken(): string | null {
    const storage = getStorage();
    return storage ? storage.getItem(STORAGE_KEY) : null;
  },

  setToken(token: string) {
    const storage = getStorage();
    if (storage) {
      storage.setItem(STORAGE_KEY, token);
    }
  },

  clear() {
    const storage = getStorage();
    if (storage) {
      storage.removeItem(STORAGE_KEY);
    }
  },
};

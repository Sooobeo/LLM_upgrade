const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

function getStorage() {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    ?.split(";")
    .map((v) => v.trim())
    .find((v) => v.startsWith(`${name}=`));
  if (!match) return null;
  return decodeURIComponent(match.split("=", 2)[1]);
}

function setCookie(name: string, value: string, days = 7) {
  if (typeof document === "undefined") return;
  const maxAge = days * 24 * 60 * 60;
  document.cookie = `${name}=${encodeURIComponent(
    value,
  )}; max-age=${maxAge}; path=/`;
}

function clearCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; max-age=0; path=/`;
}

export const auth = {
  getToken(): string | null {
    const storage = getStorage();
    const token = storage ? storage.getItem(ACCESS_KEY) : null;
    if (token) return token;
    return getCookie(ACCESS_KEY);
  },

  setToken(token: string) {
    const storage = getStorage();
    if (storage) {
      storage.setItem(ACCESS_KEY, token);
    }
    setCookie(ACCESS_KEY, token);
  },

  setSession(session: { accessToken: string; refreshToken?: string | null }) {
    this.setToken(session.accessToken);
    const storage = getStorage();
    if (storage && session.refreshToken) {
      storage.setItem(REFRESH_KEY, session.refreshToken);
    }
    if (session.refreshToken) {
      setCookie(REFRESH_KEY, session.refreshToken);
    }
  },

  getRefreshToken(): string | null {
    const storage = getStorage();
    const token = storage ? storage.getItem(REFRESH_KEY) : null;
    if (token) return token;
    return getCookie(REFRESH_KEY);
  },

  clear() {
    const storage = getStorage();
    if (storage) {
      storage.removeItem(ACCESS_KEY);
      storage.removeItem(REFRESH_KEY);
    }
    clearCookie(ACCESS_KEY);
    clearCookie(REFRESH_KEY);
  },
};

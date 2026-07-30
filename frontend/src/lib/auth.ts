let accessToken: string | null = null;
let sessionRedirectStarted = false;

const PUBLIC_AUTH_PATHS = new Set([
  "/",
  "/login",
  "/signup",
  "/auth/callback",
  "/login/google-callback",
]);

export function expireSessionAndRedirect() {
  accessToken = null;
  if (typeof window === "undefined" || sessionRedirectStarted) return;

  const currentPath = window.location.pathname.replace(/\/+$/, "") || "/";
  if (PUBLIC_AUTH_PATHS.has(currentPath)) return;

  sessionRedirectStarted = true;
  window.location.replace("/");
}

/**
 * Access tokens are intentionally kept in memory only.
 * Refresh tokens are owned by the backend's HttpOnly cookie.
 */
export const auth = {
  getToken(): string | null {
    return accessToken;
  },

  setToken(token: string) {
    accessToken = token;
    sessionRedirectStarted = false;
  },

  setSession(session: { accessToken: string; refreshToken?: string | null }) {
    accessToken = session.accessToken;
    sessionRedirectStarted = false;
  },

  getRefreshToken(): null {
    return null;
  },

  clear() {
    accessToken = null;
    sessionRedirectStarted = false;
  },
};

let accessToken: string | null = null;

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
  },

  setSession(session: { accessToken: string; refreshToken?: string | null }) {
    accessToken = session.accessToken;
  },

  getRefreshToken(): null {
    return null;
  },

  clear() {
    accessToken = null;
  },
};

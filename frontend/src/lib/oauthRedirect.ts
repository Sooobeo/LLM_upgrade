const PRODUCTION_SITE_ORIGIN = "https://happyllm.vercel.app";

function configuredProductionOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.trim();

  if (!configured) return PRODUCTION_SITE_ORIGIN;

  try {
    const url = new URL(configured);
    if (url.origin === PRODUCTION_SITE_ORIGIN) {
      return url.origin;
    }
  } catch {
    // A malformed build variable must not break the login button.
  }

  return PRODUCTION_SITE_ORIGIN;
}

export function getOAuthCallbackUrl(): string {
  const isLocalBrowser =
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1");

  const siteOrigin = isLocalBrowser
    ? window.location.origin
    : configuredProductionOrigin();

  return new URL("/auth/callback", siteOrigin).toString();
}

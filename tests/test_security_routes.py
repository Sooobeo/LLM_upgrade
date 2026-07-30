from fastapi.testclient import TestClient

from app.core.config import AppEnv, settings
from app.core.security import set_refresh_cookie
from app.main import app
from app.schemas.auth import AccessOnlyResp
from starlette.responses import Response


client = TestClient(app)


def test_llm_diagnostics_require_authentication():
    assert client.get("/health/llm/config").status_code == 401
    assert client.get("/health/llm").status_code == 401


def test_legacy_comment_read_requires_authentication():
    response = client.get(
        "/threads/988be0e0-22aa-40be-b857-1a4f545d4863/comments",
        params={"message_index": 0},
    )
    assert response.status_code == 401


def test_security_headers_are_set():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


def test_deployment_config_health_does_not_expose_secret_values():
    response = client.get("/health/config")

    assert response.status_code == 200
    assert set(response.json()) == {"ok", "app_env", "missing"}


def test_untrusted_browser_origin_is_rejected_for_refresh():
    response = client.post(
        "/auth/refresh",
        headers={"Origin": "https://attacker.example", "Sec-Fetch-Site": "cross-site"},
    )
    assert response.status_code == 403


def test_allowlisted_cross_site_origin_reaches_refresh_handler(monkeypatch):
    frontend_origin = "https://frontend.example"
    monkeypatch.setattr(settings, "CORS_ORIGINS", frontend_origin)

    response = client.post(
        "/auth/refresh",
        headers={"Origin": frontend_origin, "Sec-Fetch-Site": "cross-site"},
    )

    # There is no refresh cookie, but the trusted-origin guard must not block
    # the Vercel -> Render request before the auth handler can process it.
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_REFRESH_TOKEN"


def test_cross_site_request_without_origin_is_rejected():
    response = client.post(
        "/auth/refresh",
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert response.status_code == 403


def test_google_session_accepts_allowlisted_deployed_frontend(monkeypatch):
    frontend_origin = "https://frontend.example"
    monkeypatch.setattr(settings, "CORS_ORIGINS", frontend_origin)
    monkeypatch.setattr(
        "app.routes.auth.refresh_with_cookie",
        lambda _refresh_token: (
            AccessOnlyResp(
                access_token="access-token",
                token_type="bearer",
                expires_in=3600,
            ),
            "rotated-refresh-token",
        ),
    )

    response = client.post(
        "/auth/google/set-session",
        headers={"Origin": frontend_origin, "Sec-Fetch-Site": "cross-site"},
        json={"refresh_token": "initial-refresh-token"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "access-token"
    assert "refresh_token=rotated-refresh-token" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


def test_google_login_redirect_accepts_allowlisted_frontend(monkeypatch):
    frontend_origin = "https://frontend.example"
    monkeypatch.setattr(settings, "CORS_ORIGINS", frontend_origin)

    response = client.get(
        "/auth/google/login",
        params={"redirect_to": f"{frontend_origin}/auth/callback"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].startswith(
        f"{settings.SUPABASE_URL}/auth/v1/authorize?"
    )
    assert "provider=google" in response.headers["location"]


def test_google_login_url_supports_frontend_loading_ui(monkeypatch):
    frontend_origin = "https://frontend.example"
    monkeypatch.setattr(settings, "CORS_ORIGINS", frontend_origin)

    response = client.get(
        "/auth/google/url",
        params={"redirect_to": f"{frontend_origin}/auth/callback"},
    )

    assert response.status_code == 200
    authorize_url = response.json()["authorize_url"]
    assert authorize_url.startswith(f"{settings.SUPABASE_URL}/auth/v1/authorize?")
    assert "provider=google" in authorize_url


def test_google_login_url_accepts_project_preview_origin():
    preview_origin = "https://happyllm-preview123-sooobeo1.vercel.app"

    response = client.get(
        "/auth/google/url",
        params={"redirect_to": f"{preview_origin}/auth/callback"},
        headers={"Origin": preview_origin},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == preview_origin


def test_production_preview_login_uses_stable_callback(monkeypatch):
    preview_origin = "https://happyllm-preview123-sooobeo1.vercel.app"
    monkeypatch.setattr(settings, "APP_ENV", AppEnv.prod)
    monkeypatch.setattr(
        settings,
        "CORS_ORIGINS",
        "https://happyllm.vercel.app",
    )

    response = client.get(
        "/auth/google/url",
        params={"redirect_to": f"{preview_origin}/auth/callback"},
        headers={"Origin": preview_origin},
    )

    assert response.status_code == 200
    assert (
        "redirect_to=https%3A%2F%2Fhappyllm.vercel.app"
        in response.json()["authorize_url"]
    )


def test_google_login_url_rejects_untrusted_redirect():
    response = client.get(
        "/auth/google/url",
        params={"redirect_to": "https://attacker.example/auth/callback"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REDIRECT"


def test_google_login_url_reports_missing_backend_configuration(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "")

    response = client.get("/auth/google/url")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AUTH_NOT_CONFIGURED"


def test_production_refresh_cookie_supports_cross_site_frontend(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", AppEnv.prod)
    response = Response()

    set_refresh_cookie(response, "refresh-token")

    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=none" in cookie
    assert "Secure" in cookie

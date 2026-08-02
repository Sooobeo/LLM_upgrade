import pytest

from app.core.config import AppEnv, Settings


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("local", AppEnv.local),
        ("dev", AppEnv.dev),
        ("development", AppEnv.dev),
        ("prod", AppEnv.prod),
        ("production", AppEnv.prod),
        (" PRODUCTION ", AppEnv.prod),
    ],
)
def test_app_env_accepts_common_deployment_names(raw_value, expected):
    config = Settings(
        _env_file=None,
        APP_ENV=raw_value,
        SUPABASE_URL="https://project.example.supabase.co/",
        SUPABASE_ANON_KEY="anon-key",
    )

    assert config.APP_ENV == expected
    assert config.SUPABASE_URL == "https://project.example.supabase.co"


def test_settings_can_start_and_report_missing_supabase_configuration():
    config = Settings(
        _env_file=None,
        APP_ENV="production",
        SUPABASE_URL="",
        SUPABASE_ANON_KEY="",
    )

    assert config.APP_ENV == AppEnv.prod
    assert config.missing_required_settings == [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
    ]


def test_default_gemini_model_uses_current_flash(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_2_5_COMPAT_MODEL", raising=False)
    config = Settings(_env_file=None)

    assert config.GEMINI_MODEL == "gemini-3.6-flash"
    assert config.GEMINI_2_5_COMPAT_MODEL == "gemini-3.6-flash"


def test_vercel_preview_origin_is_narrowly_allowlisted():
    config = Settings(
        _env_file=None,
        SUPABASE_URL="https://project.example.supabase.co",
        SUPABASE_ANON_KEY="anon-key",
    )

    assert config.is_allowed_origin("https://happyllm.vercel.app")
    assert config.is_allowed_origin(
        "https://happyllm-20pq6zxeo-sooobeo1.vercel.app"
    )
    assert not config.is_allowed_origin("https://attacker-sooobeo1.vercel.app")
    assert not config.is_allowed_origin("https://happyllm.attacker.vercel.app")
    assert not config.is_allowed_origin(
        "https://happyllm-preview123-other-team.vercel.app"
    )


def test_production_origin_survives_stale_render_cors_environment():
    config = Settings(
        _env_file=None,
        CORS_ORIGINS="https://old-frontend.example.com",
        CORS_ORIGIN_REGEX="",
        SUPABASE_URL="https://project.example.supabase.co",
        SUPABASE_ANON_KEY="anon-key",
    )

    assert config.is_allowed_origin("https://happyllm.vercel.app")
    assert "https://happyllm.vercel.app" in config.cors_origins
    assert "https://old-frontend.example.com" in config.cors_origins

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

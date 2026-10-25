import importlib
import json
import os
import secrets
import subprocess
import sys

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView


def load_settings(module, overrides=None, missing=()):
    """Load settings in isolation so production tests cannot mutate Django globals."""
    process_env = {
        key: value for key, value in os.environ.items() if not key.startswith(("DJANGO_", "DB_"))
    }
    process_env.update(
        DJANGO_READ_DOT_ENV_FILE="False",
        DJANGO_SECRET_KEY=secrets.token_urlsafe(64),
        DJANGO_PIN_PEPPER=secrets.token_urlsafe(48),
        DJANGO_ALLOWED_HOSTS="api.example.test",
        DB_PASSWORD=secrets.token_urlsafe(32),
    )
    process_env.update(overrides or {})
    for key in missing:
        process_env.pop(key, None)
    script = f"""
import importlib, json
s = importlib.import_module({module!r})
print(json.dumps({{
    "debug": s.DEBUG,
    "hosts": s.ALLOWED_HOSTS,
    "sslmode": s.DATABASES["default"]["OPTIONS"]["sslmode"],
    "secure_session": getattr(s, "SESSION_COOKIE_SECURE", False),
    "secure_csrf": getattr(s, "CSRF_COOKIE_SECURE", False),
    "https_redirect": getattr(s, "SECURE_SSL_REDIRECT", False),
    "proxy_header": getattr(s, "SECURE_PROXY_SSL_HEADER", None),
    "cors": s.CORS_ALLOWED_ORIGINS,
    "cors_credentials": s.CORS_ALLOW_CREDENTIALS,
    "csrf": s.CSRF_TRUSTED_ORIGINS,
    "database_name": s.DATABASES["default"]["NAME"],
    "database_port": s.DATABASES["default"]["PORT"],
}}))
"""
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=settings.BASE_DIR,
        env=process_env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_database_and_project_defaults():
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert settings.TIME_ZONE == "Asia/Kathmandu"
    assert settings.USE_TZ is True
    assert settings.DEFAULT_AUTO_FIELD == "django.db.models.BigAutoField"


@pytest.mark.parametrize(
    "label",
    ["core", "accounts", "restaurants", "menu", "orders", "kitchen", "billing", "inventory"],
)
def test_module_app_configs(label):
    assert apps.get_app_config(label).name == f"apps.{label}"


@pytest.mark.django_db
def test_custom_user_migration_and_admin_registration():
    user_model = get_user_model()
    user = user_model.objects.create_user(username="foundation-test")
    assert user.pk is not None
    assert not user.has_usable_password()
    assert user_model._meta.db_table == "accounts_user"
    assert admin.site.is_registered(user_model)


def test_api_defaults_require_authenticated_access():
    class ProtectedView(APIView):
        def get(self, request):
            return Response({"private": True})

    response = ProtectedView.as_view()(APIRequestFactory().get("/"))
    assert response.status_code == 403
    assert settings.REST_FRAMEWORK["DEFAULT_VERSIONING_CLASS"].endswith("NamespaceVersioning")


def test_cors_defaults_do_not_allow_every_origin():
    assert settings.CORS_ALLOW_ALL_ORIGINS is False
    result = load_settings("config.settings.development")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["cors_credentials"] is False


def test_production_enforces_security_even_if_debug_env_is_true():
    result = load_settings("config.settings.production", {"DJANGO_DEBUG": "True"})
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    assert config["debug"] is False
    assert config["sslmode"] == "require"
    assert config["secure_session"] is True
    assert config["secure_csrf"] is True
    assert config["https_redirect"] is True
    assert config["proxy_header"] is None


def test_environment_values_are_parsed():
    result = load_settings(
        "config.settings.development",
        {
            "DJANGO_DEBUG": "False",
            "DB_NAME": "isolated_configuration_test",
            "DB_PORT": "55439",
            "DJANGO_CORS_ALLOWED_ORIGINS": "https://frontend.example.test",
            "DJANGO_CORS_ALLOW_CREDENTIALS": "True",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://frontend.example.test",
        },
    )
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    assert config["debug"] is False
    assert config["database_name"] == "isolated_configuration_test"
    assert config["database_port"] == 55439
    assert config["cors"] == ["https://frontend.example.test"]
    assert config["cors_credentials"] is True
    assert config["csrf"] == ["https://frontend.example.test"]


def test_proxy_trust_requires_explicit_opt_in():
    result = load_settings("config.settings.production", {"DJANGO_BEHIND_HTTPS_PROXY": "True"})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["proxy_header"] == ["HTTP_X_FORWARDED_PROTO", "https"]


@pytest.mark.parametrize("variable", ["DJANGO_SECRET_KEY", "DJANGO_PIN_PEPPER", "DB_PASSWORD"])
@pytest.mark.parametrize("missing", [True, False])
def test_required_secrets_fail_closed(variable, missing):
    overrides = {} if missing else {variable: ""}
    result = load_settings(
        "config.settings.development", overrides, missing=[variable] if missing else []
    )
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert variable in result.stderr


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"DJANGO_ALLOWED_HOSTS": ""}, "DJANGO_ALLOWED_HOSTS"),
        ({"DJANGO_ALLOWED_HOSTS": "*"}, "DJANGO_ALLOWED_HOSTS"),
        ({"DJANGO_SECRET_KEY": "placeholder"}, "DJANGO_SECRET_KEY"),
        ({"DB_SSLMODE": "disable"}, "DB_SSLMODE"),
        ({"DB_SSLMODE": "prefer"}, "DB_SSLMODE"),
        ({"DJANGO_PIN_PEPPER": "short"}, "DJANGO_PIN_PEPPER"),
        ({"DJANGO_PIN_PEPPER": "x" * 48}, "DJANGO_PIN_PEPPER"),
    ],
)
def test_production_rejects_unsafe_configuration(overrides, expected):
    result = load_settings("config.settings.production", overrides)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert expected in result.stderr


def test_base_settings_are_not_used_as_an_entrypoint():
    assert settings.SETTINGS_MODULE in {"config.settings.development", "config.settings.production"}
    assert importlib.util.find_spec("config.asgi") is not None
    assert importlib.util.find_spec("config.wsgi") is not None

import pytest
from django.core.exceptions import ImproperlyConfigured
from typesafe_sdk import TypeSafeClient

from wagtail_jev.client import get_client
from wagtail_jev.laya import LayaClient
from wagtail_jev.profiles import get_profile
from wagtail_jev.settings import get_setting

def test_jev_is_the_default():
    assert get_profile().name == "Jev"


def test_the_backend_setting_selects_laya(settings):
    settings.WAGTAIL_JEV_BACKEND = "laya"
    assert get_profile().name == "Laya"


def test_an_unknown_backend_names_the_allowed_values(settings):
    settings.WAGTAIL_JEV_BACKEND = "gpt"
    with pytest.raises(ImproperlyConfigured, match=r"'jev'.*'laya'.*'gpt'"):
        get_profile()


@pytest.mark.parametrize("backend", ["jev", "laya", "clef"])
def test_settings_override_the_model_defaults(settings, backend):
    settings.WAGTAIL_JEV_BACKEND = backend
    settings.WAGTAIL_JEV_MAX_CHARS = 5
    settings.WAGTAIL_JEV_INSTRUCTIONS = "Q {tag}"
    assert get_setting("WAGTAIL_JEV_MAX_CHARS") == 5
    assert get_setting("WAGTAIL_JEV_INSTRUCTIONS") == "Q {tag}"


def test_jev_opens_a_typesafe_client():
    client = get_client()
    try:
        assert isinstance(client, TypeSafeClient)
    finally:
        client.close()


def test_laya_opens_a_laya_client_from_the_laya_settings(settings, monkeypatch):
    settings.WAGTAIL_JEV_BACKEND = "laya"
    settings.WAGTAIL_JEV_LAYA_URL = "http://laya:8000/"
    settings.WAGTAIL_JEV_LAYA_API_KEY = None
    settings.WAGTAIL_JEV_LAYA_MODEL = "multilingual"
    settings.WAGTAIL_JEV_TIMEOUT = 7.0
    monkeypatch.setenv("LAYA_API_KEY", "from-env")

    client = get_client()

    assert isinstance(client, LayaClient)
    assert (client.url, client.api_key, client.model, client.timeout) == (
        "http://laya:8000/v1/systemone", "from-env", "multilingual", 7.0,
    )


def test_the_laya_key_setting_wins_over_the_environment(settings, monkeypatch):
    settings.WAGTAIL_JEV_BACKEND = "laya"
    settings.WAGTAIL_JEV_LAYA_API_KEY = "from-settings"
    monkeypatch.setenv("LAYA_API_KEY", "from-env")
    assert get_client().api_key == "from-settings"


def test_laya_without_a_url_runs_in_process(settings):
    settings.WAGTAIL_JEV_BACKEND = "laya"
    assert get_client().url is None


def test_clef_opens_a_client_from_the_clef_settings(settings, monkeypatch):
    opened = {}
    monkeypatch.setattr("wagtail_jev.clef.make_client", lambda **config: opened.update(config))
    settings.WAGTAIL_JEV_BACKEND = "clef"
    settings.WAGTAIL_JEV_CLEF_ACCOUNT_ID = "from-settings"
    settings.WAGTAIL_JEV_CLEF_MODEL = "clef-flash"
    settings.WAGTAIL_JEV_TIMEOUT = 7.0
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account-from-env")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token-from-env")

    get_client()

    assert opened == {"account_id": "from-settings", "api_token": "token-from-env", "model": "clef-flash", "timeout": 7.0}


@pytest.mark.parametrize("backend", ["jev", "laya", "clef"])
def test_an_explicit_none_max_chars_still_means_no_cut_off(settings, backend):
    # At 40d4f23 `clip()` did text[:None], so None meant "send the whole page"; keep that.
    from wagtail_jev.client import clip

    settings.WAGTAIL_JEV_BACKEND = backend
    settings.WAGTAIL_JEV_MAX_CHARS = None
    assert len(clip("x" * 20000)) == 20000

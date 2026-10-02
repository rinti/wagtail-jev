import pytest
from django.core.exceptions import ImproperlyConfigured
from typesafe_sdk import TypeSafeClient

from wagtail_jev.client import get_client
from wagtail_jev.laya import LayaClient
from wagtail_jev.profiles import get_profile
from wagtail_jev.settings import get_setting

JEV_INSTRUCTIONS = (
    "Would an editor file the article in `article` under the tag {tag}? "
    "Judge by the article's actual subject matter, not by incidental mentions."
)


def test_jev_is_the_default():
    assert get_profile().name == "Jev"


def test_the_backend_setting_selects_laya(settings):
    settings.WAGTAIL_JEV_BACKEND = "laya"
    assert get_profile().name == "Laya"


def test_an_unknown_backend_names_the_allowed_values(settings):
    settings.WAGTAIL_JEV_BACKEND = "gpt"
    with pytest.raises(ImproperlyConfigured, match=r"'jev'.*'laya'.*'gpt'"):
        get_profile()


def test_jev_defaults_are_unchanged():
    assert get_setting("WAGTAIL_JEV_MAX_CHARS") == 12000
    assert get_setting("WAGTAIL_JEV_INSTRUCTIONS") == JEV_INSTRUCTIONS
    assert get_setting("WAGTAIL_JEV_CRITERIA_TRUE") == (
        "The article is substantially about, or clearly belongs to, the topic {tag}."
    )
    assert get_setting("WAGTAIL_JEV_CRITERIA_FALSE") == "The topic {tag} is absent or only mentioned in passing."
    assert get_profile().quote_tags is True
    assert get_profile().slow_start is False


def test_laya_has_its_own_defaults(settings):
    settings.WAGTAIL_JEV_BACKEND = "laya"
    assert get_setting("WAGTAIL_JEV_MAX_CHARS") == 2000
    assert get_setting("WAGTAIL_JEV_INSTRUCTIONS") == "Is `state` about {tag}?"
    assert get_setting("WAGTAIL_JEV_CRITERIA_TRUE") == "about {tag}"
    assert get_setting("WAGTAIL_JEV_CRITERIA_FALSE") == "not about {tag}"
    assert get_profile().quote_tags is False
    assert get_profile().slow_start is True


@pytest.mark.parametrize("backend", ["jev", "laya"])
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


@pytest.mark.parametrize("backend", ["jev", "laya"])
def test_an_explicit_none_max_chars_still_means_no_cut_off(settings, backend):
    # At 40d4f23 `clip()` did text[:None], so None meant "send the whole page"; keep that.
    from wagtail_jev.client import clip

    settings.WAGTAIL_JEV_BACKEND = backend
    settings.WAGTAIL_JEV_MAX_CHARS = None
    assert len(clip("x" * 20000)) == 20000

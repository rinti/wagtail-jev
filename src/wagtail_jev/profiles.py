"""What differs between the decision models wagtail-jev can use.

A :class:`ModelProfile` holds everything model-specific: the name editors see, how to open a
client, the defaults of the model-specific settings (the tag prompt and the text cut-off),
how an Article becomes tag state, how an Article or an Excerpt becomes rating state,
whether tag names are quoted, and whether the first request after a restart is slow.
``WAGTAIL_JEV_BACKEND`` picks one; everything else in wagtail-jev is shared.

Laya's differences were measured on real content: with Jev's prompt and dict state it barely
told relevant from irrelevant tags, while a short question about plain text, with unquoted
tag names, separated them in English and Swedish. It also reads only about 2,000
characters of state. Laya reads Ratings as plain text too, so every Laya request has the
same kind of state.

This is internal for now: the seam a public model interface can grow from.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from django.core.exceptions import ImproperlyConfigured

from wagtail_jev.settings import get_setting


@dataclass(frozen=True)
class ModelProfile:
    name: str
    make_client: Callable[[], Any]
    defaults: Mapping[str, Any]
    tag_state: Callable[[Any, str], Any]  # (article, clipped body) -> state
    rating_state: Callable[[str | None, str], Any]  # (title, None for an excerpt; clipped text) -> state
    quote_tags: bool
    slow_start: bool = False


def _jev_client():
    from typesafe_sdk import TypeSafeClient

    return TypeSafeClient(
        api_key=get_setting("WAGTAIL_JEV_API_KEY"),
        model=get_setting("WAGTAIL_JEV_MODEL"),
        timeout=get_setting("WAGTAIL_JEV_TIMEOUT"),
    )


def _laya_client():
    from wagtail_jev.laya import LayaClient

    return LayaClient(
        url=get_setting("WAGTAIL_JEV_LAYA_URL"),
        api_key=get_setting("WAGTAIL_JEV_LAYA_API_KEY") or os.environ.get("LAYA_API_KEY"),
        model=get_setting("WAGTAIL_JEV_LAYA_MODEL"),
        timeout=get_setting("WAGTAIL_JEV_TIMEOUT"),
    )


def _jev_tag_state(article, body: str) -> dict:
    return {"article": {"title": article.title, "body": body}, "existing_tags": list(article.existing_tags)}


def _laya_tag_state(article, body: str) -> str:
    return f"{article.title}\n\n{body}"


def _jev_rating_state(title: str | None, text: str) -> dict:
    if title is None:
        return {"text": text}
    return {"article": {"title": title, "body": text}}


def _laya_rating_state(title: str | None, text: str) -> str:
    return text if title is None else f"{title}\n\n{text}"


JEV = ModelProfile(
    name="Jev",
    make_client=_jev_client,
    defaults={
        "WAGTAIL_JEV_MAX_CHARS": 12000,
        "WAGTAIL_JEV_INSTRUCTIONS": (
            "Would an editor file the article in `article` under the tag {tag}? "
            "Judge by the article's actual subject matter, not by incidental mentions."
        ),
        "WAGTAIL_JEV_CRITERIA_TRUE": "The article is substantially about, or clearly belongs to, the topic {tag}.",
        "WAGTAIL_JEV_CRITERIA_FALSE": "The topic {tag} is absent or only mentioned in passing.",
    },
    tag_state=_jev_tag_state,
    rating_state=_jev_rating_state,
    quote_tags=True,
)

LAYA = ModelProfile(
    name="Laya",
    make_client=_laya_client,
    defaults={
        "WAGTAIL_JEV_MAX_CHARS": 2000,
        "WAGTAIL_JEV_INSTRUCTIONS": "Is `state` about {tag}?",
        "WAGTAIL_JEV_CRITERIA_TRUE": "about {tag}",
        "WAGTAIL_JEV_CRITERIA_FALSE": "not about {tag}",
    },
    tag_state=_laya_tag_state,
    rating_state=_laya_rating_state,
    quote_tags=False,
    slow_start=True,
)

PROFILES = {"jev": JEV, "laya": LAYA}


def get_profile() -> ModelProfile:
    """The profile ``WAGTAIL_JEV_BACKEND`` names; raises :class:`ImproperlyConfigured` otherwise."""
    backend = get_setting("WAGTAIL_JEV_BACKEND")
    try:
        return PROFILES[backend]
    except (KeyError, TypeError):
        allowed = ", ".join(repr(key) for key in PROFILES)
        raise ImproperlyConfigured(f"WAGTAIL_JEV_BACKEND must be one of {allowed}, got {backend!r}") from None

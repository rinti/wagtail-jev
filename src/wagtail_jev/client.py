"""The Jev connection: a ``TypeSafeClient`` built from the ``WAGTAIL_JEV_*`` settings.

Tests replace :func:`get_client` to substitute a fake."""

from __future__ import annotations

from typesafe_sdk import TypeSafeClient

from wagtail_jev.settings import get_setting


def get_client() -> TypeSafeClient:
    return TypeSafeClient(
        api_key=get_setting("WAGTAIL_JEV_API_KEY"),
        model=get_setting("WAGTAIL_JEV_MODEL"),
        timeout=get_setting("WAGTAIL_JEV_TIMEOUT"),
    )

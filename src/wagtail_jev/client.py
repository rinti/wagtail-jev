"""The Jev connection: everything about talking to Jev that is not a domain question.

:func:`ask` sends one request. It opens a ``TypeSafeClient`` from the ``WAGTAIL_JEV_*``
settings and closes it afterwards, unless the caller passes a ``client`` of its own,
which is used as-is and left open so one connection can serve many requests.
:func:`clip` cuts text to ``WAGTAIL_JEV_MAX_CHARS`` so requests stay inside Jev's
token budget. Tests replace :func:`get_client` to substitute a fake.
"""

from __future__ import annotations

import logging
from typing import Mapping

from typesafe_sdk import SystemOneResponse, TypeSafeClient

from wagtail_jev.settings import get_setting

logger = logging.getLogger(__name__)


def get_client() -> TypeSafeClient:
    return TypeSafeClient(
        api_key=get_setting("WAGTAIL_JEV_API_KEY"),
        model=get_setting("WAGTAIL_JEV_MODEL"),
        timeout=get_setting("WAGTAIL_JEV_TIMEOUT"),
    )


def ask(
    state: dict, questions: Mapping[str, object], *, client: TypeSafeClient | None = None
) -> SystemOneResponse:
    """Put ``questions`` about ``state`` to Jev in one request.

    With no ``client`` a connection is opened for this call and closed afterwards, even
    on error. A given ``client`` is used as-is and left open.
    """
    owns_client = client is None
    client = client or get_client()
    try:
        response = client.system_one(state, questions)
    finally:
        if owns_client:
            client.close()
    logger.info("jev answered %d questions with %s", len(questions), response.model)
    return response


def clip(text: str) -> str:
    """``text`` cut to ``WAGTAIL_JEV_MAX_CHARS``."""
    return text[: get_setting("WAGTAIL_JEV_MAX_CHARS")]

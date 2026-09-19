"""Pure classification layer: text + candidate tags in, scored suggestions out.

Each candidate tag becomes one Noul question ("does this article belong under
tag X?"). Questions in a request run in parallel and cannot see each other, so
a tag is judged independently and several may apply. Ranking happens here;
thresholding and capping are the Tag field's job, so policy changes need no re-inference.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Sequence

from typesafe_sdk import Noul, NoulCriteria, TypeSafeClient

from wagtail_jev.settings import get_setting

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TagSuggestion:
    name: str
    probability: float

    @property
    def percent(self) -> int:
        return round(self.probability * 100)


def build_state(*, title: str, body: str, existing_tags: Sequence[str] = ()) -> dict:
    return {
        "article": {"title": title, "body": body},
        "existing_tags": list(existing_tags),
    }


@dataclass(frozen=True)
class PromptTemplates:
    """Templates for the per-tag question. ``{tag}`` is replaced with the tag name."""

    instructions: str
    criteria_true: str
    criteria_false: str

    @classmethod
    def from_settings(cls) -> "PromptTemplates":
        return cls(
            instructions=get_setting("WAGTAIL_JEV_INSTRUCTIONS"),
            criteria_true=get_setting("WAGTAIL_JEV_CRITERIA_TRUE"),
            criteria_false=get_setting("WAGTAIL_JEV_CRITERIA_FALSE"),
        )


def build_question(tag: str, templates: PromptTemplates) -> Noul:
    quoted = repr(tag)
    return Noul(
        instructions=templates.instructions.format(tag=quoted),
        criteria=NoulCriteria(
            true=templates.criteria_true.format(tag=quoted),
            false=templates.criteria_false.format(tag=quoted),
        ),
    )


def _chunks(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def get_client() -> TypeSafeClient:
    return TypeSafeClient(
        api_key=get_setting("WAGTAIL_JEV_API_KEY"),
        model=get_setting("WAGTAIL_JEV_MODEL"),
        timeout=get_setting("WAGTAIL_JEV_TIMEOUT"),
    )


def score_tags(
    *,
    title: str,
    body: str,
    candidates: Sequence[str],
    templates: PromptTemplates,
    existing_tags: Sequence[str] = (),
    client: TypeSafeClient | None = None,
) -> list[TagSuggestion]:
    """Return a probability for every candidate, unfiltered and sorted high to low.

    Thresholding and capping belong to the Tag field (``wagtail_jev.tag_field``).
    """
    candidates = list(dict.fromkeys(c for c in candidates if c and c.strip()))
    if not candidates:
        return []

    body = body[: get_setting("WAGTAIL_JEV_MAX_CHARS")]
    state = build_state(title=title, body=body, existing_tags=existing_tags)
    owns_client = client is None
    client = client or get_client()
    results: list[TagSuggestion] = []
    try:
        for batch in _chunks(candidates, get_setting("WAGTAIL_JEV_BATCH_SIZE")):
            questions = {f"tag_{i}": build_question(tag, templates) for i, tag in enumerate(batch)}
            response = client.system_one(state, questions)
            logger.info("jev classified %d tags with %s", len(batch), response.model)
            for i, tag in enumerate(batch):
                results.append(TagSuggestion(tag, response.nouls[f"tag_{i}"].noul))
    finally:
        if owns_client:
            client.close()
    results.sort(key=lambda s: s.probability, reverse=True)
    return results


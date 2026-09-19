"""The Tag field: one taggable manager on a page, with its own tag model, prompt
templates, threshold and cap. The one place that turns an Article into Suggestions.

``JevTagField`` is what a page declares in ``jev_tag_fields``; every attribute may be
``None`` meaning "use the ``WAGTAIL_JEV_*`` setting". ``JevTagField.bind`` resolves
those defaults against a model and field name once, producing a ``BoundTagField``.
Its ``score`` asks Jev one Noul question per candidate tag ("does this article belong
under tag X?") and returns every probability; ``suggest`` keeps those at or above the
threshold, capped. Questions in a request run in parallel and cannot see each other,
so each tag is judged independently and several may apply.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from django.apps import apps
from django.utils.module_loading import import_string
from typesafe_sdk import Noul, NoulCriteria, TypeSafeClient

from wagtail_jev import client as jev_client
from wagtail_jev.article import Article
from wagtail_jev.settings import get_setting

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TagSuggestion:
    """One candidate tag with Jev's probability that it applies."""

    name: str
    probability: float

    @property
    def percent(self) -> int:
        return round(self.probability * 100)


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


@dataclass(frozen=True)
class JevTagField:
    """Per-field configuration. Every attribute defaults to the ``WAGTAIL_JEV_*`` settings.

    :param templates: prompt templates used for this field's tags.
    :param candidates: callable returning candidate tag names. Defaults to every
        row of the tag model behind the field.
    :param threshold: minimum probability for a suggestion.
    :param max_tags: cap on suggestions.
    """

    templates: PromptTemplates | None = None
    candidates: Callable[[], Iterable[str]] | None = None
    threshold: float | None = None
    max_tags: int | None = None

    def bind(self, model, field_name: str) -> "BoundTagField":
        """Resolve every ``None`` against the settings for ``field_name`` on ``model``."""
        return BoundTagField(
            model=model,
            name=field_name,
            templates=self.templates or PromptTemplates.from_settings(),
            candidate_source=self.candidates or _default_candidate_source(model, field_name),
            threshold=get_setting("WAGTAIL_JEV_THRESHOLD") if self.threshold is None else self.threshold,
            max_tags=get_setting("WAGTAIL_JEV_MAX_TAGS") if self.max_tags is None else self.max_tags,
        )


@dataclass(frozen=True)
class BoundTagField:
    """A :class:`JevTagField` resolved against a model and the settings. No ``None`` here."""

    model: type
    name: str
    templates: PromptTemplates
    candidate_source: Callable[[], Iterable[str]]
    threshold: float
    max_tags: int | None

    def candidates(self, article: Article) -> list[str]:
        """Candidate tag names for this field, minus the Article's existing tags."""
        return [c for c in self.candidate_source() if c not in article.existing_tags]

    def score(self, article: Article, *, client: TypeSafeClient | None = None) -> list[TagSuggestion]:
        """A probability for every candidate tag, unfiltered, sorted high to low.

        One Noul question per candidate, sent in batches of ``WAGTAIL_JEV_BATCH_SIZE``.
        Blank and duplicate candidates are dropped; no candidates means no request.
        A ``client`` you pass is used as-is and left open; otherwise one is opened and
        closed for this call.
        """
        candidates = list(dict.fromkeys(c for c in self.candidates(article) if c and c.strip()))
        if not candidates:
            return []

        state = _state(article)
        owns_client = client is None
        client = client or jev_client.get_client()
        results: list[TagSuggestion] = []
        try:
            for batch in _chunks(candidates, get_setting("WAGTAIL_JEV_BATCH_SIZE")):
                questions = {f"tag_{i}": self._question(tag) for i, tag in enumerate(batch)}
                response = client.system_one(state, questions)
                logger.info("jev classified %d tags with %s", len(batch), response.model)
                for i, tag in enumerate(batch):
                    results.append(TagSuggestion(tag, response.nouls[f"tag_{i}"].noul))
        finally:
            if owns_client:
                client.close()
        results.sort(key=lambda s: s.probability, reverse=True)
        return results

    def suggest(self, article: Article, *, client: TypeSafeClient | None = None) -> list[TagSuggestion]:
        """:meth:`score`, keeping only suggestions at or above the threshold, capped at
        ``max_tags``."""
        kept = [s for s in self.score(article, client=client) if s.probability >= self.threshold]
        return kept[: self.max_tags] if self.max_tags else kept

    def _question(self, tag: str) -> Noul:
        quoted = repr(tag)
        return Noul(
            instructions=self.templates.instructions.format(tag=quoted),
            criteria=NoulCriteria(
                true=self.templates.criteria_true.format(tag=quoted),
                false=self.templates.criteria_false.format(tag=quoted),
            ),
        )


def _state(article: Article) -> dict:
    return {
        "article": {"title": article.title, "body": article.body[: get_setting("WAGTAIL_JEV_MAX_CHARS")]},
        "existing_tags": list(article.existing_tags),
    }


def _chunks(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _default_candidate_source(model, field_name: str) -> Callable[[], Iterable[str]]:
    """``WAGTAIL_JEV_CANDIDATES`` if set, else all rows of the field's tag model."""
    source = get_setting("WAGTAIL_JEV_CANDIDATES")
    if isinstance(source, str):
        source = import_string(source)
    if callable(source):
        return source

    def from_tag_model():
        tag_model = _tag_model_for_field(model, field_name)
        return tag_model.objects.order_by("name").values_list("name", flat=True)

    return from_tag_model


def _tag_model_for_field(model, field_name: str):
    """The tag model behind a ``ClusterTaggableManager``/``TaggableManager``, falling back
    to ``WAGTAIL_JEV_TAG_MODEL`` when the field has no ``through`` model."""
    try:
        return model._meta.get_field(field_name).through.tag_model()
    except Exception:
        return apps.get_model(get_setting("WAGTAIL_JEV_TAG_MODEL"))

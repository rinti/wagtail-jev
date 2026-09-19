"""The Tag field: one taggable manager on a page, with its own tag model, prompt
templates, threshold and cap.

``JevTagField`` is what a page declares in ``jev_tag_fields``; every attribute may be
``None`` meaning "use the ``WAGTAIL_JEV_*`` setting". ``JevTagField.bind`` resolves
those defaults against a model and field name once, producing a ``BoundTagField``
whose ``suggest`` runs the whole pipeline: candidate tags, minus existing tags,
scored, thresholded and capped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from django.apps import apps
from django.utils.module_loading import import_string

from wagtail_jev.article import Article
from wagtail_jev.classifier import PromptTemplates, TagSuggestion, score_tags
from wagtail_jev.settings import get_setting


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

    def suggest(self, article: Article, *, client=None) -> list[TagSuggestion]:
        """Score the candidates against ``article``; keep those at or above the
        threshold, capped at ``max_tags``, sorted high to low."""
        scored = score_tags(
            title=article.title,
            body=article.body,
            candidates=self.candidates(article),
            existing_tags=article.existing_tags,
            templates=self.templates,
            client=client,
        )
        kept = [s for s in scored if s.probability >= self.threshold]
        return kept[: self.max_tags] if self.max_tags else kept


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

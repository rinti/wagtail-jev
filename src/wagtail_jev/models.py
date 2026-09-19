"""Mixin for pages that can be tagged by Jev."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from wagtail_jev.candidates import candidate_tag_names
from wagtail_jev.classifier import PromptTemplates, TagSuggestion, suggest_tags
from wagtail_jev.text import page_text


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
    candidates: Callable[[], list[str]] | None = None
    threshold: float | None = None
    max_tags: int | None = None


class JevTaggableMixin:
    """Add to a Page subclass that has one or more ``ClusterTaggableManager`` fields.

    Set ``jev_text_fields`` to the fields whose content describes the article and
    ``jev_tag_fields`` to a mapping of tag field name to :class:`JevTagField`.
    """

    jev_text_fields: tuple[str, ...] = ("title", "body")
    jev_tag_fields: Mapping[str, JevTagField] = {"tags": JevTagField()}

    @classmethod
    def jev_tag_field_config(cls, field_name: str) -> JevTagField:
        try:
            return cls.jev_tag_fields[field_name]
        except KeyError:
            raise LookupError(
                f"{cls.__name__} has no Jev tag field {field_name!r}; "
                f"configured: {', '.join(cls.jev_tag_fields) or 'none'}"
            ) from None

    @classmethod
    def jev_candidates(cls, field_name: str) -> list[str]:
        config = cls.jev_tag_field_config(field_name)
        return candidate_tag_names(cls, field_name, config.candidates)

    def jev_text(self) -> str:
        return page_text(self, [f for f in self.jev_text_fields if f != "title"])

    def jev_existing_tags(self, field_name: str) -> list[str]:
        return [tag.name for tag in getattr(self, field_name).all()]

    def jev_suggest_tags(self, field_name: str, **kwargs) -> list[TagSuggestion]:
        config = self.jev_tag_field_config(field_name)
        existing = self.jev_existing_tags(field_name)
        candidates = [c for c in self.jev_candidates(field_name) if c not in existing]
        kwargs.setdefault("templates", config.templates)
        kwargs.setdefault("threshold", config.threshold)
        kwargs.setdefault("max_tags", config.max_tags)
        return suggest_tags(
            title=self.title,
            body=self.jev_text(),
            candidates=candidates,
            existing_tags=existing,
            **kwargs,
        )

    def jev_add_tags(self, field_name: str, names) -> None:
        getattr(self, field_name).add(*names)

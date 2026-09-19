"""Mixin for pages that can be tagged by Jev."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from wagtail_jev.article import Article
from wagtail_jev.candidates import candidate_tag_names
from wagtail_jev.classifier import PromptTemplates, TagSuggestion, suggest_tags


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

    @classmethod
    def jev_suggest_for_article(
        cls, field_name: str, article: Article, **kwargs
    ) -> list[TagSuggestion]:
        """Score ``field_name``'s candidates against an :class:`Article`.

        Uses the field's :class:`JevTagField` for templates, threshold and cap unless
        overridden in ``kwargs``; a ``client`` may be passed through to reuse a session.
        """
        config = cls.jev_tag_field_config(field_name)
        candidates = [c for c in cls.jev_candidates(field_name) if c not in article.existing_tags]
        kwargs.setdefault("templates", config.templates)
        kwargs.setdefault("threshold", config.threshold)
        kwargs.setdefault("max_tags", config.max_tags)
        return suggest_tags(
            title=article.title,
            body=article.body,
            candidates=candidates,
            existing_tags=article.existing_tags,
            **kwargs,
        )

    def jev_suggest_tags(self, field_name: str, **kwargs) -> list[TagSuggestion]:
        """Score ``field_name`` against this page's saved content."""
        return self.jev_suggest_for_article(field_name, Article.from_page(self, field_name), **kwargs)

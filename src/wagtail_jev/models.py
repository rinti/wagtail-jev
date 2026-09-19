"""Mixin for pages that can be tagged by Jev."""

from __future__ import annotations

from typing import Mapping

from wagtail_jev.article import Article
from wagtail_jev.classifier import TagSuggestion
from wagtail_jev.tag_field import BoundTagField, JevTagField

__all__ = ["JevTagField", "JevTaggableMixin"]


class JevTaggableMixin:
    """Add to a Page subclass that has one or more ``ClusterTaggableManager`` fields.

    Set ``jev_text_fields`` to the fields whose content describes the article and
    ``jev_tag_fields`` to a mapping of tag field name to :class:`JevTagField`.
    """

    jev_text_fields: tuple[str, ...] = ("title", "body")
    jev_tag_fields: Mapping[str, JevTagField] = {"tags": JevTagField()}

    @classmethod
    def jev_tag_field(cls, field_name: str) -> BoundTagField:
        """The Tag field ``field_name``, with its settings defaults resolved.

        Raises :class:`LookupError` if the field is not in ``jev_tag_fields``.
        """
        try:
            config = cls.jev_tag_fields[field_name]
        except KeyError:
            raise LookupError(
                f"{cls.__name__} has no Jev tag field {field_name!r}; "
                f"configured: {', '.join(cls.jev_tag_fields) or 'none'}"
            ) from None
        return config.bind(cls, field_name)

    def jev_suggest_tags(self, field_name: str, *, client=None) -> list[TagSuggestion]:
        """Score ``field_name`` against this page's saved content."""
        article = Article.from_page(self, field_name)
        return self.jev_tag_field(field_name).suggest(article, client=client)

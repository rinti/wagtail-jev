"""Mixin for pages that Jev can tag and rate."""

from __future__ import annotations

from typing import Mapping

from wagtail_jev.article import Article
from wagtail_jev.classifier import TagSuggestion
from wagtail_jev.quality import BoundQuality, Level, Quality, Rating, rate
from wagtail_jev.tag_field import BoundTagField, JevTagField

__all__ = ["JevTagField", "JevTaggableMixin", "Level", "Quality"]


class JevTaggableMixin:
    """Add to a Page subclass that has one or more ``ClusterTaggableManager`` fields.

    Set ``jev_text_fields`` to the fields whose text makes up the Article,
    ``jev_tag_fields`` to a mapping of tag field name to :class:`JevTagField`, and
    ``jev_qualities`` to a mapping of key to :class:`Quality` for Ratings.
    """

    jev_text_fields: tuple[str, ...] = ("title", "body")
    jev_tag_fields: Mapping[str, JevTagField] = {"tags": JevTagField()}
    jev_qualities: Mapping[str, Quality] = {}

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

    @classmethod
    def jev_quality(cls, key: str) -> BoundQuality:
        """The Quality declared under ``key``, checked and bound to this model.

        Raises :class:`LookupError` if the key is not in ``jev_qualities``.
        """
        try:
            quality = cls.jev_qualities[key]
        except KeyError:
            raise LookupError(
                f"{cls.__name__} has no Jev quality {key!r}; "
                f"configured: {', '.join(cls.jev_qualities) or 'none'}"
            ) from None
        return quality.bind(cls, key)

    @classmethod
    def jev_bound_qualities(cls, *keys: str) -> list[BoundQuality]:
        """The bound Qualities for ``keys``, or every declared Quality when none are given.

        Always in declaration order, whatever order the keys are given in.
        Raises :class:`LookupError` for an unknown key.
        """
        wanted = {key: cls.jev_quality(key) for key in keys or cls.jev_qualities}
        return [wanted[key] for key in cls.jev_qualities if key in wanted]

    def jev_rate(self, *keys: str, client=None) -> list[Rating]:
        """Rate this page's saved Article on the Qualities ``keys``, or on every declared
        Quality when none are given, in one Jev request.

        Ratings come back in declaration order whatever order the keys are given in.
        Raises :class:`LookupError` for an unknown key before any request is made.
        """
        return rate(self.jev_bound_qualities(*keys), Article.from_page(self), client=client)

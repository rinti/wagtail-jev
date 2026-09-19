"""The Article: what Jev reads about a page, built from a saved page or from unsaved form data.

Both adapters produce the same value, so the "title is separate from body" rule,
the ``jev_text_fields`` iteration and the text flattening live here and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import models
from django.utils.html import strip_tags
from taggit.utils import parse_tags
from wagtail.blocks import StreamValue, StructValue
from wagtail.fields import RichTextField, StreamField
from wagtail.rich_text import RichText


@dataclass(frozen=True)
class Article:
    title: str
    body: str
    existing_tags: tuple[str, ...] = ()

    @classmethod
    def from_page(cls, page, field_name: str | None = None) -> "Article":
        """Build from a saved page instance and the tags currently on Tag field ``field_name``.

        Without a Tag field (as when rating a Quality) the Article carries no existing tags.
        """
        parts = (_value_to_text(getattr(page, name, None)) for name in _body_fields(page))
        existing = tuple(tag.name for tag in getattr(page, field_name).all()) if field_name else ()
        return cls(title=page.title, body=_join(parts), existing_tags=existing)

    @classmethod
    def from_form_data(cls, model, data, files=None, *, field_name: str | None = None) -> "Article":
        """Build from the page edit form's raw POST data, so unsaved edits count.

        ``field_name`` is the Tag field whose unsaved tags become the existing tags; omit
        it to build an Article with none.
        """
        parts = (_value_from_form(model, name, data, files or {}) for name in _body_fields(model))
        existing = tuple(parse_tags(data.get(field_name, ""))) if field_name else ()
        return cls(title=data.get("title", ""), body=_join(parts), existing_tags=existing)


def _body_fields(model_or_page) -> list[str]:
    return [f for f in model_or_page.jev_text_fields if f != "title"]


def _join(parts) -> str:
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def _value_from_form(model, name, data, files) -> str:
    try:
        field = model._meta.get_field(name)
    except Exception:
        return ""
    if isinstance(field, StreamField):
        if f"{name}-count" not in data:
            return ""
        value = field.stream_block.value_from_datadict(data, files, name)
    elif isinstance(field, (RichTextField, models.CharField, models.TextField)):
        value = data.get(name, "")
    else:
        return ""
    return _value_to_text(value)


def _value_to_text(value) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, RichText):
        return strip_tags(value.source)
    if isinstance(value, str):
        return strip_tags(value)
    if isinstance(value, (int, float)):
        return ""
    if isinstance(value, StreamValue):
        return "\n".join(filter(None, (_value_to_text(child.value) for child in value)))
    if isinstance(value, (StructValue, dict)):
        return "\n".join(filter(None, (_value_to_text(v) for v in value.values())))
    if isinstance(value, (list, tuple)):
        return "\n".join(filter(None, (_value_to_text(v) for v in value)))
    return ""

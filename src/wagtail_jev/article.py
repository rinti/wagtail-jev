"""What Jev reads: the Article for a whole page, the Excerpt for one of its text fields.

Both are built from a saved page or from unsaved form data, so the "title is separate
from body" rule, the ``jev_text_fields`` iteration, the supported field types and the
text flattening live here and nowhere else.
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


@dataclass(frozen=True)
class Excerpt:
    """The flattened text of one text field on a page, and nothing else: no title, no tags."""

    text: str

    @classmethod
    def from_page(cls, page, field_name: str) -> "Excerpt":
        """Build from the saved value of ``field_name``; raises :class:`LookupError` for a
        field that is not one of the supported text field types."""
        text_field(type(page), field_name)
        return cls(text=_value_to_text(getattr(page, field_name, None)).strip())

    @classmethod
    def from_form_data(cls, model, field_name: str, data, files=None) -> "Excerpt":
        """Build from the page edit form's raw POST data, so unsaved edits count.

        Raises :class:`LookupError` for a field that is not one of the supported text
        field types; a supported field missing from the form gives a blank Excerpt.
        """
        text_field(model, field_name)
        return cls(text=_value_from_form(model, field_name, data, files or {}).strip())


TEXT_FIELD_TYPES = (RichTextField, StreamField, models.CharField, models.TextField)


def text_field(model, field_name: str):
    """The model field ``field_name`` if it is a type the Article and Excerpt can read.

    Raises :class:`LookupError` naming the field when it is unknown or of another type.
    """
    try:
        field = model._meta.get_field(field_name)
    except Exception:
        raise LookupError(f"{model.__name__} has no field {field_name!r}") from None
    if not isinstance(field, TEXT_FIELD_TYPES):
        raise LookupError(
            f"{model.__name__}.{field_name} is a {type(field).__name__}, not a text field Jev can read "
            f"({', '.join(t.__name__ for t in TEXT_FIELD_TYPES)})"
        )
    return field


def _body_fields(model_or_page) -> list[str]:
    return [f for f in model_or_page.jev_text_fields if f != "title"]


def _join(parts) -> str:
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def _value_from_form(model, name, data, files) -> str:
    try:
        field = text_field(model, name)
    except LookupError:
        return ""
    if isinstance(field, StreamField):
        if f"{name}-count" not in data:
            return ""
        value = field.stream_block.value_from_datadict(data, files, name)
    elif isinstance(field, RichTextField):
        # The editor posts the rich text widget's own format (Draftail: contentstate
        # JSON), not HTML, so let the widget turn it into HTML before flattening.
        if not data.get(name):
            return ""
        value = field.formfield().widget.value_from_datadict(data, files, name)
    else:
        value = data.get(name, "")
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

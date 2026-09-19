"""Turn page field values into plain text for the Jev ``state``."""

from __future__ import annotations

from django.utils.html import strip_tags
from wagtail.blocks import StreamValue, StructValue
from wagtail.rich_text import RichText


def value_to_text(value) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, RichText):
        return strip_tags(value.source)
    if isinstance(value, str):
        return strip_tags(value)
    if isinstance(value, (int, float)):
        return ""
    if isinstance(value, StreamValue):
        return "\n".join(filter(None, (value_to_text(child.value) for child in value)))
    if isinstance(value, StructValue):
        return "\n".join(filter(None, (value_to_text(v) for v in value.values())))
    if isinstance(value, dict):
        return "\n".join(filter(None, (value_to_text(v) for v in value.values())))
    if isinstance(value, (list, tuple)):
        return "\n".join(filter(None, (value_to_text(v) for v in value)))
    return ""


def page_text(page, field_names) -> str:
    parts = []
    for name in field_names:
        parts.append(value_to_text(getattr(page, name, None)))
    return "\n\n".join(p.strip() for p in parts if p and p.strip())

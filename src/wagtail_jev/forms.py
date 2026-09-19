"""Rebuild page text from raw editor form data, so suggestions reflect unsaved edits."""

from django.db import models
from wagtail.fields import RichTextField, StreamField

from wagtail_jev.text import value_to_text


def text_from_form_data(model, field_names, data, files=None):
    parts = []
    for name in field_names:
        try:
            field = model._meta.get_field(name)
        except Exception:
            continue
        if isinstance(field, StreamField):
            if f"{name}-count" not in data:
                continue
            value = field.stream_block.value_from_datadict(data, files or {}, name)
        elif isinstance(field, (RichTextField, models.CharField, models.TextField)):
            value = data.get(name, "")
        else:
            continue
        text = value_to_text(value)
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)

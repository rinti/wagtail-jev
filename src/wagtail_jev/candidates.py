"""Where candidate tag names come from."""

from __future__ import annotations

from typing import Callable

from django.apps import apps
from django.utils.module_loading import import_string

from wagtail_jev.settings import get_setting


def tag_model_for_field(model, field_name):
    """Return the tag model behind a ``ClusterTaggableManager``/``TaggableManager``.

    Falls back to ``WAGTAIL_JEV_TAG_MODEL`` when the field has no ``through`` model
    (or is not a taggable manager at all).
    """
    try:
        field = model._meta.get_field(field_name)
        return field.through.tag_model()
    except Exception:
        return apps.get_model(get_setting("WAGTAIL_JEV_TAG_MODEL"))


def candidate_tag_names(model=None, field_name=None, source: Callable | str | None = None):
    """Candidate names for one tag field.

    Priority: explicit ``source`` callable, then ``WAGTAIL_JEV_CANDIDATES`` setting,
    then all rows of the field's tag model.
    """
    if source is None:
        source = get_setting("WAGTAIL_JEV_CANDIDATES")
    if isinstance(source, str):
        source = import_string(source)
    if callable(source):
        return list(source())
    if model is None:
        tag_model = apps.get_model(get_setting("WAGTAIL_JEV_TAG_MODEL"))
    else:
        tag_model = tag_model_for_field(model, field_name)
    return list(tag_model.objects.order_by("name").values_list("name", flat=True))

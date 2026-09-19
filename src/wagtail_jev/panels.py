import json

from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, Panel

from wagtail_jev.article import text_field
from wagtail_jev.models import JevTaggableMixin


class JevTagFieldPanel(FieldPanel):
    """A ``FieldPanel`` for a tag field with a "Let Jev suggest tags" button beneath it.

    Use it in ``content_panels`` in place of ``FieldPanel("tags")`` on a page
    that mixes in :class:`wagtail_jev.models.JevTaggableMixin`.
    """

    class BoundPanel(FieldPanel.BoundPanel):
        template_name = "wagtail_jev/panels/tag_field_panel.html"

        class Media:
            js = ["wagtail_jev/js/jev-suggest-controller.js"]

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context["jev_url"] = reverse("wagtail_jev:suggest")
            context["jev_model"] = self.instance._meta.label
            context["jev_messages"] = json.dumps(
                {
                    "loading": str(_("Asking Jev…")),
                    "empty": str(_("No tags passed the confidence threshold.")),
                    "added": str(_("Added: ")),
                    "error": str(_("Jev error: ")),
                }
            )
            return context


class JevRatingPanel(Panel):
    """A panel with a "Rate with Jev" button that rates the whole Article on the page's Qualities.

    Place it anywhere in a panel list on a page that mixes in
    :class:`wagtail_jev.models.JevTaggableMixin`. ``keys`` picks a subset of the declared
    Qualities; omit it to rate every one. Ratings are only displayed, never saved.
    """

    def __init__(self, keys=None, heading=_("Ratings"), **kwargs):
        super().__init__(heading=heading, **kwargs)
        self.keys = tuple(keys) if keys else ()

    def clone_kwargs(self):
        kwargs = super().clone_kwargs()
        kwargs["keys"] = self.keys
        return kwargs

    def on_model_bound(self):
        _check_rating_model(self)
        # Fail loudly here on a typo in ``keys``, not when an editor presses the button.
        self.model.jev_bound_qualities(*self.keys)

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtail_jev/panels/rating_panel.html"

        class Media:
            js = ["wagtail_jev/js/jev-rate-controller.js"]

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context.update(
                _rating_context(
                    self.panel.model,
                    self.panel.keys,
                    empty=_("Nothing to rate yet: the page has no text."),
                )
            )
            return context


class JevRatingFieldPanel(FieldPanel):
    """A ``FieldPanel`` for a text field with a "Rate with Jev" button beneath it that rates
    just that field's Excerpt on the Qualities ``keys``.

    Works on ``RichTextField``, ``StreamField``, ``CharField`` and ``TextField``. When one
    Quality is attached the button names it. Ratings are only displayed, never saved.
    """

    def __init__(self, field_name, *, keys, **kwargs):
        super().__init__(field_name, **kwargs)
        self.keys = tuple(keys)

    def clone_kwargs(self):
        kwargs = super().clone_kwargs()
        kwargs["keys"] = self.keys
        return kwargs

    def on_model_bound(self):
        super().on_model_bound()
        _check_rating_model(self)
        # Fail loudly here on a typo in ``keys`` or a field Jev cannot read, not on button press.
        self.model.jev_bound_qualities(*self.keys)
        text_field(self.model, self.field_name)

    class BoundPanel(FieldPanel.BoundPanel):
        template_name = "wagtail_jev/panels/rating_field_panel.html"

        class Media:
            js = ["wagtail_jev/js/jev-rate-controller.js"]

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context.update(
                _rating_context(
                    self.panel.model,
                    self.panel.keys,
                    field_name=self.panel.field_name,
                    empty=_("Nothing to rate yet: the field has no text."),
                )
            )
            return context


def _check_rating_model(panel):
    if not issubclass(panel.model, JevTaggableMixin):
        raise ImproperlyConfigured(
            f"{type(panel).__name__} needs {panel.model.__name__} to mix in JevTaggableMixin"
        )


def _rating_context(model, keys, *, empty, field_name="") -> dict:
    """Template context shared by both rating panels: the endpoint, the subject and the keys.

    ``keys`` is rendered as an explicit list so the "default to every Quality" choice is
    resolved at render time, not by the controller.
    """
    qualities = model.jev_bound_qualities(*keys)
    if len(qualities) == 1:
        button_label = _("Rate %(quality)s with Jev") % {"quality": qualities[0].label}
    else:
        button_label = _("Rate with Jev")
    return {
        "jev_url": reverse("wagtail_jev:rate"),
        "jev_model": model._meta.label,
        "jev_field": field_name,
        "jev_keys": ",".join(quality.key for quality in qualities),
        "jev_button_label": button_label,
        "jev_messages": json.dumps(
            {
                "loading": str(_("Asking Jev…")),
                "empty": str(empty),
                "error": str(_("Jev error: ")),
            }
        ),
    }

import json

from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, Panel

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
        if not issubclass(self.model, JevTaggableMixin):
            raise ImproperlyConfigured(
                f"JevRatingPanel needs {self.model.__name__} to mix in JevTaggableMixin"
            )
        # Fail loudly here on a typo in ``keys``, not when an editor presses the button.
        self.model.jev_bound_qualities(*self.keys)

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtail_jev/panels/rating_panel.html"

        class Media:
            js = ["wagtail_jev/js/jev-rate-controller.js"]

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            qualities = self.panel.model.jev_bound_qualities(*self.panel.keys)
            context["jev_url"] = reverse("wagtail_jev:rate")
            context["jev_model"] = self.panel.model._meta.label
            context["jev_keys"] = ",".join(quality.key for quality in qualities)
            context["jev_messages"] = json.dumps(_rating_messages())
            return context


def _rating_messages() -> dict[str, str]:
    return {
        "loading": str(_("Asking Jev…")),
        "empty": str(_("Nothing to rate yet: the page has no text.")),
        "error": str(_("Jev error: ")),
    }

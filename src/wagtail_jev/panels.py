import json

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel


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

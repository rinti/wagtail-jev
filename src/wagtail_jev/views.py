from django.apps import apps
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from taggit.utils import parse_tags
from typesafe_sdk import TypeSafeError
from wagtail.admin.auth import require_admin_access

from wagtail_jev.classifier import suggest_tags
from wagtail_jev.forms import text_from_form_data
from wagtail_jev.models import JevTaggableMixin


@require_admin_access
@require_POST
def suggest(request):
    """Score one tag field's candidates against the editor's current (unsaved) content.

    Expects the page edit form's data plus ``jev_model`` (``app_label.ModelName``)
    and ``jev_field`` (the tag field name). Returns
    ``{"tags": [{"name": ..., "probability": ...}]}``.
    """
    try:
        model = apps.get_model(request.POST.get("jev_model", ""))
    except (LookupError, ValueError):
        return JsonResponse({"error": "Unknown model"}, status=400)
    if not issubclass(model, JevTaggableMixin):
        return JsonResponse({"error": "Model is not JevTaggable"}, status=400)

    field_name = request.POST.get("jev_field", "")
    try:
        config = model.jev_tag_field_config(field_name)
    except LookupError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    title = request.POST.get("title", "")
    body = text_from_form_data(
        model,
        [f for f in model.jev_text_fields if f != "title"],
        request.POST,
        request.FILES,
    )
    existing = parse_tags(request.POST.get(field_name, ""))
    candidates = [c for c in model.jev_candidates(field_name) if c not in existing]

    try:
        suggestions = suggest_tags(
            title=title,
            body=body,
            candidates=candidates,
            existing_tags=existing,
            templates=config.templates,
            threshold=config.threshold,
            max_tags=config.max_tags,
        )
    except TypeSafeError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse(
        {"tags": [{"name": s.name, "probability": s.probability} for s in suggestions]}
    )

from django.apps import apps
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from typesafe_sdk import TypeSafeError
from wagtail.admin.auth import require_admin_access

from wagtail_jev.article import Article, Excerpt
from wagtail_jev.models import JevTaggableMixin
from wagtail_jev.quality import Rating, rate as rate_qualities


def _jev_model(request):
    """The JevTaggable model named by ``jev_model``, or a 400 response."""
    try:
        model = apps.get_model(request.POST.get("jev_model", ""))
    except (LookupError, ValueError):
        return None, JsonResponse({"error": "Unknown model"}, status=400)
    if not issubclass(model, JevTaggableMixin):
        return None, JsonResponse({"error": "Model is not JevTaggable"}, status=400)
    return model, None


@require_admin_access
@require_POST
def suggest(request):
    """Score one tag field's candidates against the editor's current (unsaved) content.

    Expects the page edit form's data plus ``jev_model`` (``app_label.ModelName``)
    and ``jev_field`` (the tag field name). Returns
    ``{"tags": [{"name": ..., "probability": ...}]}``.
    """
    model, error = _jev_model(request)
    if error:
        return error

    field_name = request.POST.get("jev_field", "")
    try:
        tag_field = model.jev_tag_field(field_name)
    except LookupError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    article = Article.from_form_data(model, request.POST, request.FILES, field_name=field_name)
    try:
        suggestions = tag_field.suggest(article)
    except TypeSafeError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse(
        {"tags": [{"name": s.name, "probability": s.probability} for s in suggestions]}
    )


@require_admin_access
@require_POST
def rate(request):
    """Rate the editor's current (unsaved) text on the model's Qualities in one Jev request.

    Expects the page edit form's data plus ``jev_model`` (``app_label.ModelName``) and
    zero or more ``jev_keys``; no keys means every declared Quality. With ``jev_field``
    the subject is that field's Excerpt, otherwise the whole Article. Returns
    ``{"ratings": [...]}`` in declaration order, each Rating with its key and label, the
    most likely level's label and probability, and every level's label and probability.
    Ratings are never written anywhere.
    """
    model, error = _jev_model(request)
    if error:
        return error

    try:
        qualities = model.jev_bound_qualities(*request.POST.getlist("jev_keys"))
    except LookupError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    field_name = request.POST.get("jev_field", "")
    try:
        if field_name:
            subject = Excerpt.from_form_data(model, field_name, request.POST, request.FILES)
        else:
            subject = Article.from_form_data(model, request.POST, request.FILES)
    except LookupError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        ratings = rate_qualities(qualities, subject)
    except TypeSafeError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse({"ratings": [_rating_json(r) for r in ratings]})


def _rating_json(rating: Rating) -> dict:
    return {
        "key": rating.key,
        "label": rating.label,
        "top_label": rating.top_label,
        "top_probability": rating.top_probability,
        "levels": [
            {"label": level.label, "probability": probability}
            for level, probability in zip(rating.levels, rating.probabilities)
        ],
    }

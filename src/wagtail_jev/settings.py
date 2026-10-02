"""Flat ``WAGTAIL_JEV_*`` Django settings with defaults."""

from django.conf import settings

DEFAULTS = {
    # Which decision model answers: "jev" (TypeSafe's hosted Jev) or "laya" (open source, runs locally).
    "WAGTAIL_JEV_BACKEND": "jev",
    # Base URL of a Laya server (`python -m laya.serve`). Unset means Laya runs in this process.
    "WAGTAIL_JEV_LAYA_URL": None,
    # Bearer key for that server, matching its LAYA_API_KEY. Falls back to the LAYA_API_KEY environment variable.
    "WAGTAIL_JEV_LAYA_API_KEY": None,
    # Laya checkpoint, e.g. "english" or "multilingual". None lets Laya pick one per request by language.
    "WAGTAIL_JEV_LAYA_MODEL": None,
    # TypeSafe API key. Falls back to the TYPESAFE_API_KEY environment variable.
    "WAGTAIL_JEV_API_KEY": None,
    # Model sent with every request. Pin a versioned ID once thresholds are tuned.
    "WAGTAIL_JEV_MODEL": "jev-latest",
    # Minimum Noul probability for a tag to count as suggested.
    "WAGTAIL_JEV_THRESHOLD": 0.6,
    # Upper bound on suggestions returned per page. None means no cap.
    "WAGTAIL_JEV_MAX_TAGS": None,
    # Characters of page text sent as state. Unset means the model's default (Jev 12000,
    # Laya 2000); None means no cut-off.
    "WAGTAIL_JEV_MAX_CHARS": None,
    # Candidate tags per request. Each tag is one question; questions share the 64k budget.
    "WAGTAIL_JEV_BATCH_SIZE": 40,
    # Dotted path of the taggit model whose rows are the candidate tags.
    "WAGTAIL_JEV_TAG_MODEL": "taggit.Tag",
    # Dotted path to a callable returning candidate tag names. Overrides the tag model.
    "WAGTAIL_JEV_CANDIDATES": None,
    # Request timeout in seconds.
    "WAGTAIL_JEV_TIMEOUT": 30.0,
    # Prompt templates. ``{tag}`` is replaced with the candidate tag name. Unset means the
    # model's default (see wagtail_jev.profiles): Jev reads the article under the `article`
    # state key (with `article.title` and `article.body`) and current tags under
    # `existing_tags`; Laya reads the page as plain text, which it calls `state`.
    "WAGTAIL_JEV_INSTRUCTIONS": None,
    "WAGTAIL_JEV_CRITERIA_TRUE": None,
    "WAGTAIL_JEV_CRITERIA_FALSE": None,
}


# Settings whose default depends on the model; resolved from its profile when not set at all.
# An explicit None keeps its old meaning (e.g. WAGTAIL_JEV_MAX_CHARS = None: no cut-off).
MODEL_DEFAULTS = (
    "WAGTAIL_JEV_MAX_CHARS",
    "WAGTAIL_JEV_INSTRUCTIONS",
    "WAGTAIL_JEV_CRITERIA_TRUE",
    "WAGTAIL_JEV_CRITERIA_FALSE",
)


def get_setting(name):
    if name in MODEL_DEFAULTS and not hasattr(settings, name):
        from wagtail_jev.profiles import get_profile  # imported here: profiles imports this module

        return get_profile().defaults[name]
    return getattr(settings, name, DEFAULTS[name])

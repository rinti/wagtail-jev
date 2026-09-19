"""Flat ``WAGTAIL_JEV_*`` Django settings with defaults."""

from django.conf import settings

DEFAULTS = {
    # TypeSafe API key. Falls back to the TYPESAFE_API_KEY environment variable.
    "WAGTAIL_JEV_API_KEY": None,
    # Model sent with every request. Pin a versioned ID once thresholds are tuned.
    "WAGTAIL_JEV_MODEL": "jev-latest",
    # Minimum Noul probability for a tag to count as suggested.
    "WAGTAIL_JEV_THRESHOLD": 0.6,
    # Upper bound on suggestions returned per page. None means no cap.
    "WAGTAIL_JEV_MAX_TAGS": None,
    # Characters of page text sent as state; keeps well inside the 32k token budget.
    "WAGTAIL_JEV_MAX_CHARS": 12000,
    # Candidate tags per request. Each tag is one question; questions share the 64k budget.
    "WAGTAIL_JEV_BATCH_SIZE": 40,
    # Dotted path of the taggit model whose rows are the candidate tags.
    "WAGTAIL_JEV_TAG_MODEL": "taggit.Tag",
    # Dotted path to a callable returning candidate tag names. Overrides the tag model.
    "WAGTAIL_JEV_CANDIDATES": None,
    # Request timeout in seconds.
    "WAGTAIL_JEV_TIMEOUT": 30.0,
    # Prompt templates. ``{tag}`` is replaced with the candidate tag name.
    # The article is available to the model under the `article` state key
    # (with `article.title` and `article.body`), current tags under `existing_tags`.
    "WAGTAIL_JEV_INSTRUCTIONS": (
        "Would an editor file the article in `article` under the tag {tag}? "
        "Judge by the article's actual subject matter, not by incidental mentions."
    ),
    "WAGTAIL_JEV_CRITERIA_TRUE": (
        "The article is substantially about, or clearly belongs to, the topic {tag}."
    ),
    "WAGTAIL_JEV_CRITERIA_FALSE": "The topic {tag} is absent or only mentioned in passing.",
}


def get_setting(name):
    return getattr(settings, name, DEFAULTS[name])

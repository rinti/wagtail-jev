# wagtail-jev

Let [Jev](https://docs.typesafe.ai), TypeSafe's System One model, suggest tags for
Wagtail pages. Editors get a **Let Jev suggest tags** button under the tag field; it
scores every existing tag against the page content currently in the editor and adds
the ones that pass a confidence threshold.

Each candidate tag is one yes/no (Noul) question, all fanned out in a single request.
Thresholding, capping and ranking happen in your code, so tuning needs no re-inference.

## Install

```sh
pip install wagtail-jev
```

```python
INSTALLED_APPS = [
    "wagtail_jev",
    ...
]

WAGTAIL_JEV_API_KEY = env("TYPESAFE_API_KEY")  # or leave unset and export TYPESAFE_API_KEY
```

## Use

```python
from modelcluster.contrib.taggit import ClusterTaggableManager
from wagtail.models import Page

from wagtail_jev.models import JevTaggableMixin
from wagtail_jev.panels import JevTagFieldPanel


class ArticlePage(JevTaggableMixin, Page):
    intro = RichTextField(blank=True)
    body = StreamField([...], blank=True)
    tags = ClusterTaggableManager(through="blog.ArticleTag", blank=True)

    jev_text_fields = ("title", "intro", "body")  # what Jev reads
    # jev_tag_fields = {"tags": JevTagField()}    # default

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
        JevTagFieldPanel("tags"),  # instead of FieldPanel("tags")
    ]
```

`JevTagFieldPanel` renders the normal tag widget plus the button. The button posts the
unsaved form data to an admin endpoint, so suggestions reflect what the editor is
looking at. Returned tags are appended to the tag widget; nothing is saved until the
editor saves the page.

### Several tag fields

A page can have any number of tag fields, each with its own tag model, prompts
and threshold. Candidates default to every row of the tag model behind the field,
so a `feeling_tags` manager whose through model points at `FeelingTag` is only
ever offered feelings.

```python
from wagtail_jev.classifier import PromptTemplates
from wagtail_jev.models import JevTagField, JevTaggableMixin


class ArticlePage(JevTaggableMixin, Page):
    tags = ClusterTaggableManager(through="blog.ArticleTag", blank=True)
    feeling_tags = ClusterTaggableManager(
        through="blog.ArticleFeeling", blank=True, related_name="feeling_tagged"
    )

    jev_tag_fields = {
        "tags": JevTagField(),
        "feeling_tags": JevTagField(
            templates=PromptTemplates(
                instructions="Does the mood of `article` match {tag}?",
                criteria_true="A reader would come away feeling {tag}.",
                criteria_false="{tag} does not describe the article's tone.",
            ),
            threshold=0.8,
            candidates=lambda: ["calm", "tense", "joyful"],  # optional override
        ),
    }

    content_panels = Page.content_panels + [
        JevTagFieldPanel("tags"),
        JevTagFieldPanel("feeling_tags"),
    ]
```

`JevTagField` attributes (`templates`, `candidates`, `threshold`, `max_tags`) all
default to the corresponding `WAGTAIL_JEV_*` settings.

### Bulk tagging

```sh
manage.py jev_tag_pages blog.ArticlePage            # print suggestions
manage.py jev_tag_pages blog.ArticlePage --apply    # save as new draft revisions
manage.py jev_tag_pages blog.ArticlePage --apply --publish --threshold 0.8 --ids 12 34
manage.py jev_tag_pages blog.ArticlePage --field feeling_tags   # default: all jev_tag_fields
```

### In code

```python
from wagtail_jev.classifier import suggest_tags

for s in suggest_tags(title=..., body=..., candidates=["python", "django"]):
    print(s.name, s.probability)
```

## Settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `WAGTAIL_JEV_API_KEY` | `None` | Falls back to `TYPESAFE_API_KEY` env var |
| `WAGTAIL_JEV_MODEL` | `"jev-latest"` | Pin a versioned ID once thresholds are tuned |
| `WAGTAIL_JEV_THRESHOLD` | `0.6` | Minimum probability for a tag to be suggested |
| `WAGTAIL_JEV_MAX_TAGS` | `None` | Cap on suggestions per page |
| `WAGTAIL_JEV_MAX_CHARS` | `12000` | Body text sent to Jev is truncated to this |
| `WAGTAIL_JEV_BATCH_SIZE` | `40` | Candidate tags per request |
| `WAGTAIL_JEV_TAG_MODEL` | `"taggit.Tag"` | Model whose rows are the candidate tags |
| `WAGTAIL_JEV_CANDIDATES` | `None` | Dotted path to a callable returning tag names; overrides the model |
| `WAGTAIL_JEV_TIMEOUT` | `30.0` | Request timeout in seconds |
| `WAGTAIL_JEV_INSTRUCTIONS` | see below | Question template |
| `WAGTAIL_JEV_CRITERIA_TRUE` | see below | What a "yes" means |
| `WAGTAIL_JEV_CRITERIA_FALSE` | see below | What a "no" means |

### Prompts

`{tag}` is replaced with the quoted tag name. The page is available to the model as
`article.title` and `article.body`; the page's current tags as `existing_tags`.

```python
WAGTAIL_JEV_INSTRUCTIONS = (
    "Would an editor file the article in `article` under the tag {tag}? "
    "Judge by the article's actual subject matter, not by incidental mentions."
)
WAGTAIL_JEV_CRITERIA_TRUE = "The article is substantially about, or clearly belongs to, the topic {tag}."
WAGTAIL_JEV_CRITERIA_FALSE = "The topic {tag} is absent or only mentioned in passing."
```

Per-field override: pass `PromptTemplates(...)` as `templates` on the field's
`JevTagField` (see "Several tag fields" above).

## Tuning

Start with the default threshold, run `jev_tag_pages` without `--apply` on a sample
of pages, and compare against editor judgment. Raise the threshold if you see false
positives; lower it or adjust the prompt if good tags are missed. Non-English content
works but is less accurate; test on your own data.

## Development

```sh
uv venv && uv pip install -e ".[test]"
pytest
```

Manual check of the editor button against a stubbed Jev client:

```sh
python tests/manual_e2e.py          # stubbed Jev, no network
python tests/manual_e2e.py --live   # real Jev; reads WAGTAIL_API_KEY or TYPESAFE_API_KEY from .env
```

Then log in at http://127.0.0.1:8765/admin/ as `admin` / `pw` and open the "Django tips" page.

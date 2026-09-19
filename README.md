# wagtail-jev

Let [Jev](https://docs.typesafe.ai), TypeSafe's System One model, suggest tags for
Wagtail pages and rate their text on Qualities you declare. Editors get a **Let Jev
suggest tags** button under the tag field; it scores every existing tag against the
page content currently in the editor and adds the ones that pass a confidence
threshold. A **Rate with Jev** button shows how the page, or one field of it, reads on
a rubric such as readability or mood.

Each candidate tag is one yes/no (Noul) question, each Quality one rubric (Score)
question, all fanned out in a single request. Thresholding, capping and ranking happen
in your code, so tuning needs no re-inference.

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

A saved page scores itself:

```python
for s in page.jev_suggest_tags("tags"):
    print(s.name, s.probability)
```

Or take the Tag field and hand it any `Article`. `jev_tag_field()` resolves the
field's `JevTagField` against the `WAGTAIL_JEV_*` settings once, and `suggest()`
runs the whole pipeline: candidates minus existing tags, scored, thresholded, capped.

```python
from wagtail_jev.article import Article

tag_field = ArticlePage.jev_tag_field("tags")
article = Article(title="Django ORM tips", body="select_related and friends")
for s in tag_field.suggest(article):
    print(s.name, s.probability)
```

For raw probabilities with no threshold or cap, use `wagtail_jev.classifier.score_tags`.

## Qualities

Tags say what a page is about. A **Quality** is a spectrum its text is judged on: how
easy it is to understand, what mood it leaves the reader in. You declare a Quality once
on the page model as an ordered rubric of levels, and Jev answers with a **Rating**: the
most likely level plus a probability for every level. A Rating is shown in the editor
and never saved. Nothing about a Quality is a tag.

### Writing a rubric

```python
from wagtail_jev.quality import Level, Quality

READABILITY = Quality(
    label="Readability",
    instructions="How easy is the text to understand?",
    levels=(
        Level("Easy", "A first-time reader follows every sentence without slowing down."),
        Level("Moderate", "A reader has to reread a few sentences or look up a term."),
        Level("Hard", "The text assumes expert knowledge or packs several ideas into each sentence."),
    ),
)

MOOD = Quality(
    label="Mood",
    instructions="What mood does the text leave the reader in?",
    levels=(
        Level("Sad", "The text dwells on loss, failure or disappointment."),
        Level("Neutral", "The text reports facts without emotional colour."),
        Level("Happy", "The text celebrates, reassures or looks forward to something."),
    ),
)
```

Each level has a short `label` the editor sees and a `description` Jev judges. Three
rules for writing them:

- **Two to ten levels**, lowest first. Fewer or more is an error when the Quality is
  bound: when a panel binds, or the first time code looks the key up.
- **Describe a concrete situation**, not a degree. Jev judges each level on its own, so
  "A reader has to reread a few sentences" works and "Moderately readable" does not.
- **Say "the text"**, never "the article" or "the field". The same Quality then rates
  the whole Article and any single field's Excerpt.

No rubrics ship with the package; adapt these two to your site.

### In the editor

Declare each Quality under a key in `jev_qualities`, then place the panels:

```python
from wagtail_jev.panels import JevRatingFieldPanel, JevRatingPanel, JevTagFieldPanel


class ArticlePage(JevTaggableMixin, Page):
    intro = RichTextField(blank=True)
    body = StreamField([...], blank=True)
    tags = ClusterTaggableManager(through="blog.ArticleTag", blank=True)

    jev_text_fields = ("title", "intro", "body")
    jev_qualities = {"readability": READABILITY, "mood": MOOD}

    content_panels = Page.content_panels + [
        JevRatingFieldPanel("intro", keys=["readability"]),  # rates only the intro
        JevRatingFieldPanel("body", keys=["readability", "mood"]),
        JevTagFieldPanel("tags"),
        JevRatingPanel(),  # the whole Article on every Quality
    ]
```

`JevRatingPanel` adds a **Rate with Jev** button that rates the Article (the title and
every `jev_text_fields` field) on every declared Quality. It goes anywhere in a panel
list, and `keys` limits it to a subset:

```python
JevRatingPanel(keys=["readability"], heading="Readability")
```

`JevRatingFieldPanel` replaces `FieldPanel` for a `RichTextField`, `StreamField`,
`CharField` or `TextField`. Its button rates that field's **Excerpt**, the flattened text
of that one field with no title, on `keys`.

When exactly one Quality is attached, either button names it: **Rate Readability with
Jev**. Both post the unsaved form data, so Ratings reflect what the editor is looking
at. Each Rating is one line, `Readability: Easy (62%)`, with every level's probability
behind a click. One press is one Jev request however many Qualities it covers, and
empty text makes no request. An unknown key or a field Jev cannot read fails when the
panel binds, not when an editor presses the button.

### Rating in code

A saved page rates its own Article, on every Quality or a subset, in one request:

```python
for r in page.jev_rate():  # or page.jev_rate("readability")
    print(r.label, r.top_label, r.percent)  # Readability Easy 62
    for level, probability in zip(r.levels, r.probabilities):
        print(" ", level.label, probability)
```

Or take one bound Quality and hand it any `Article` or `Excerpt`:

```python
from wagtail_jev.article import Article, Excerpt

readability = ArticlePage.jev_quality("readability")
readability.rate(Article(title="Django ORM tips", body="select_related and friends"))
readability.rate(Excerpt(text="One dense paragraph."))
readability.rate(Excerpt.from_page(page, "intro"))
```

`rate()` returns `None` when there is nothing to rate. To rate several bound Qualities
in one request, pass them to `wagtail_jev.quality.rate(qualities, subject)`. Both,
like `jev_rate()`, take a `client=` keyword so tests can inject a stub `TypeSafeClient`.

Qualities have no threshold, cap or settings of their own. They share
`WAGTAIL_JEV_MODEL`, `WAGTAIL_JEV_API_KEY`, `WAGTAIL_JEV_TIMEOUT` and
`WAGTAIL_JEV_MAX_CHARS` with tagging, and need no migration.

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

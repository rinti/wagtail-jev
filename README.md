# wagtail-jev

wagtail-jev adds two buttons to the Wagtail page editor. Both send the text the editor
is writing to [Jev](https://docs.typesafe.ai), an AI model from TypeSafe, and show
what it says.

- **Let Jev suggest tags** sits under a tag field. Jev looks at every tag your site
  already has and picks the ones that fit the page.
- **Rate with Jev** rates the page, or one field of it, on a scale you define, such as
  readability or mood. The result is shown to the editor and never saved.

One button press is one request to Jev, no matter how many tags or scales it covers.
For tags, Jev returns a probability for each one. Your code decides how high that
probability must be, so you can tune it without asking Jev again.

https://github.com/user-attachments/assets/e47ef5e2-2a48-4305-b2ed-d1cabf01ba55

## Install

Install the package:

```sh
pip install wagtail-jev
```

Add it to your Django settings, together with your TypeSafe API key:

```python
INSTALLED_APPS = [
    "wagtail_jev",
    ...
]

WAGTAIL_JEV_API_KEY = "..."
```

If you leave out `WAGTAIL_JEV_API_KEY`, the `TYPESAFE_API_KEY` environment variable is
used instead.

## Use

Three changes to your page model: add `JevTaggableMixin`, list the fields Jev should
read in `jev_text_fields`, and use `JevTagFieldPanel` for the tag field:

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
    # jev_tag_fields = {"tags": JevTagField()}    # the default: tag the "tags" field

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
        JevTagFieldPanel("tags"),  # instead of FieldPanel("tags")
    ]
```

`JevTagFieldPanel` shows the normal tag widget with the button under it. The button
sends the current form contents to Jev, so unsaved edits count. Suggested tags are
added to the tag widget. Nothing is saved until the editor saves the page.

### Several tag fields

A page can have more than one tag field. Give each one its own `JevTagField` in
`jev_tag_fields`. Each can have its own question, its own threshold and its own list
of tags. By default, the list is every tag in that field's tag model.

Below, `tags` keeps the defaults. `feeling_tags` changes all three. `PromptTemplates`
holds the question, in the same three parts as the prompt settings:

```python
from wagtail_jev.models import JevTagField, PromptTemplates


class ArticlePage(JevTaggableMixin, Page):
    tags = ClusterTaggableManager(through="blog.ArticleTag", blank=True)
    feeling_tags = ClusterTaggableManager(through="blog.ArticleFeeling", blank=True)

    jev_tag_fields = {
        "tags": JevTagField(),
        "feeling_tags": JevTagField(
            templates=PromptTemplates(
                instructions="Does the mood of `article` match {tag}?",
                criteria_true="A reader would come away feeling {tag}.",
                criteria_false="{tag} does not describe the article's tone.",
            ),
            threshold=0.8,
            candidates=lambda: ["calm", "tense", "joyful"],
        ),
    }

    content_panels = Page.content_panels + [
        JevTagFieldPanel("tags"),
        JevTagFieldPanel("feeling_tags"),
    ]
```

Every `JevTagField` argument is optional. Leave one out and the matching
`WAGTAIL_JEV_*` setting from the table below is used.

### Bulk tagging

To tag many saved pages at once, use the `jev_tag_pages` management command:

```sh
manage.py jev_tag_pages blog.ArticlePage
manage.py jev_tag_pages blog.ArticlePage --apply
manage.py jev_tag_pages blog.ArticlePage --apply --publish --threshold 0.8 --ids 12 34
manage.py jev_tag_pages blog.ArticlePage --field feeling_tags
```

- With no options it only prints what Jev would suggest.
- `--apply` saves the tags as a new draft revision of each page. Add `--publish` to
  publish as well.
- `--threshold` overrides the threshold and `--ids` limits the run to those pages.
- `--field` tags one tag field. The default is every field in `jev_tag_fields`.

### In code

Call `jev_suggest_tags()` on a saved page to get its tag suggestions:

```python
for s in page.jev_suggest_tags("tags"):
    print(s.name, s.probability)
```

You can also suggest tags for text that is not a saved page. First look up the tag
field with `jev_tag_field()`. Then call its `suggest()` method with an `Article`. An
Article is just a title and a body.

`suggest()` does the same work as the button. It skips tags the Article already has,
scores the rest, and keeps only the tags above the threshold, up to the cap.

```python
from wagtail_jev.article import Article

tag_field = ArticlePage.jev_tag_field("tags")
article = Article(title="Django ORM tips", body="select_related and friends")
for s in tag_field.suggest(article):
    print(s.name, s.probability)
```

If you want every tag's probability with no threshold or cap, call
`tag_field.score(article)` instead.

## Qualities

Tags say what a page is about. A **Quality** says how the text reads. Readability is
one example. Mood is another.

You define a Quality on the page model as a list of levels, from lowest to highest.
When an editor presses the button, Jev picks the level that fits the text best. It
also gives a probability for every level. This answer is called a **Rating**. Ratings
are shown to the editor and never saved. A Quality is not a tag.

### Writing a rubric

Here are two Qualities you can copy. The first rates how easy the text is to read. The
second rates its mood.

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

Each level has a short `label` and a longer `description`. The editor sees the label.
Jev judges the text against the description. Three rules for writing levels:

- **Use two to ten levels**, lowest first. Any other number raises an error when the
  panel is set up.
- **Describe a concrete situation**, not a degree. Jev judges each level on its own.
  "A reader has to reread a few sentences" works. "Moderately readable" does not.
- **Say "the text"**, never "the article" or "the field". Then the same Quality can
  rate the whole page or a single field.

The package ships no rubrics. Copy these two and adapt them to your site.

### In the editor

Add each Quality under a key in `jev_qualities`, then place the panels:

```python
from wagtail_jev.panels import JevRatingFieldPanel, JevRatingPanel


class ArticlePage(JevTaggableMixin, Page):
    ...
    jev_qualities = {"readability": READABILITY, "mood": MOOD}

    content_panels = Page.content_panels + [
        JevRatingFieldPanel("intro", keys=["readability"]),
        JevRatingFieldPanel("body", keys=["readability", "mood"]),
        JevTagFieldPanel("tags"),
        JevRatingPanel(),
    ]
```

This gives the editor three buttons. One under the intro rates it on readability. One
under the body rates it on readability and mood. The last rates the whole page on
every Quality.

`JevRatingPanel` adds a **Rate with Jev** button for the whole page. It rates the title
plus every field in `jev_text_fields`, on every Quality. It can go anywhere in a panel
list. Pass `keys` to rate only some Qualities:

```python
JevRatingPanel(keys=["readability"], heading="Readability")
```

`JevRatingFieldPanel` replaces `FieldPanel` for one text field. It works on a
`RichTextField`, `StreamField`, `CharField` or `TextField`. Its button rates only that
field's text, on the Qualities in `keys`. That text is called the **Excerpt**.

When a button covers exactly one Quality, it is named after it, for example **Rate
Readability with Jev**.

Both buttons work the same way:

- They send the current form contents, so unsaved edits count.
- Each Rating is shown as one line, such as `Readability: Easy (62%)`. Click it to see
  the probability of every level.
- One press is one request to Jev, however many Qualities it covers.
- Empty text makes no request.
- A misspelt key, or a field Jev cannot read, raises an error when the panel is set
  up, not when an editor presses the button.

### Rating in code

A saved page has a `jev_rate()` method. It returns one Rating per Quality, from one
request to Jev:

```python
for rating in page.jev_rate():
    print(rating.label, rating.top_label, rating.percent)  # Readability Easy 62
```

To rate only some Qualities, pass their keys: `page.jev_rate("readability")`.

Each Rating also lists the probability of every level:

```python
for level, probability in zip(rating.levels, rating.probabilities):
    print(level.label, probability)
```

You can also rate text that is not a page. First look up a Quality with
`jev_quality()`. Then call its `rate()` method with the text. The text can be an
`Article` (a title and a body) or an `Excerpt` (a single piece of text):

```python
from wagtail_jev.article import Article, Excerpt

readability = ArticlePage.jev_quality("readability")
readability.rate(Article(title="Django ORM tips", body="select_related and friends"))
readability.rate(Excerpt(text="One dense paragraph."))
readability.rate(Excerpt.from_page(page, "intro"))
```

The last line reads the `intro` field from a saved page. `rate()` returns `None` when
the text is empty.

To rate one text on several Qualities in one request, use
`wagtail_jev.quality.rate(qualities, subject)`. Every rating and scoring function also takes a
`client=` argument to reuse one connection across several requests; the connection
is otherwise opened and closed per call.

Qualities have no threshold and no cap. They have no settings of their own. They use
the same model, API key, timeout and max chars settings as tagging. They need no
database migration.

## Settings

Put these in your Django settings. Only the API key is required. The tag settings can
also be set per tag field, as shown in "Several tag fields" above.

| Setting | Default | Meaning |
| --- | --- | --- |
| `WAGTAIL_JEV_API_KEY` | `None` | Your TypeSafe API key. If unset, the `TYPESAFE_API_KEY` environment variable is used |
| `WAGTAIL_JEV_MODEL` | `"jev-latest"` | Which Jev model to use. Pin a specific version once your threshold is tuned |
| `WAGTAIL_JEV_THRESHOLD` | `0.6` | A tag is suggested only if its probability is at least this |
| `WAGTAIL_JEV_MAX_TAGS` | `None` | Suggest at most this many tags per page |
| `WAGTAIL_JEV_MAX_CHARS` | `12000` | Only the first this-many characters of the page text are sent to Jev |
| `WAGTAIL_JEV_BATCH_SIZE` | `40` | How many tags to ask about in one request |
| `WAGTAIL_JEV_TAG_MODEL` | `"taggit.Tag"` | The model whose rows are the tags Jev can choose from |
| `WAGTAIL_JEV_CANDIDATES` | `None` | Dotted path to a function that returns tag names. Replaces the tag model |
| `WAGTAIL_JEV_TIMEOUT` | `30.0` | Give up on a request after this many seconds |
| `WAGTAIL_JEV_INSTRUCTIONS` | see below | The question asked about each tag |
| `WAGTAIL_JEV_CRITERIA_TRUE` | see below | What a "yes" answer means |
| `WAGTAIL_JEV_CRITERIA_FALSE` | see below | What a "no" answer means |

### Prompts

Jev answers a yes/no question about each tag. Three settings hold the wording of that
question. These are the defaults:

```python
WAGTAIL_JEV_INSTRUCTIONS = (
    "Would an editor file the article in `article` under the tag {tag}? "
    "Judge by the article's actual subject matter, not by incidental mentions."
)
WAGTAIL_JEV_CRITERIA_TRUE = "The article is substantially about, or clearly belongs to, the topic {tag}."
WAGTAIL_JEV_CRITERIA_FALSE = "The topic {tag} is absent or only mentioned in passing."
```

`{tag}` stands for the tag name. `article` is the page, with a `title` and a `body`.
`existing_tags` lists the tags the page already has. You can use all three in your own
wording.

To change the prompts for one tag field only, give its `JevTagField` a
`templates=PromptTemplates(...)` argument. The "Several tag fields" section above shows
this.

## Tuning

Start with the default threshold. Run `jev_tag_pages` without `--apply` on some pages.
Compare the output with the tags your editors would choose.

- If Jev suggests wrong tags, raise the threshold.
- If Jev misses good tags, lower the threshold or change the prompt.

Text in other languages than English works, but less accurately. Test on your own
content.

## Development

Install the package in a virtualenv and run the tests:

```sh
uv venv
uv pip install -e ".[test]"
pytest
```

To try the buttons in a browser, start a local site. It uses a fake Jev, so it needs
no API key:

```sh
python tests/manual_e2e.py
```

Log in at http://127.0.0.1:8765/admin/ with the username `admin` and the password
`pw`. Then open the "Django tips" page.

Add `--live` to use the real Jev. The script reads the API key from `WAGTAIL_API_KEY`
or `TYPESAFE_API_KEY` in your `.env` file.

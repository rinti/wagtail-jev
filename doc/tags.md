# Tag suggestions

wagtail-jev gives tag suggestions in four steps:

1. wagtail-jev collects the candidate tags of the tag field.
   These are all the tags in the tag model of the field, minus the existing tags of the page.
2. wagtail-jev sends one yes/no question for each candidate tag to Jev.
3. Jev gives a probability for each candidate tag.
4. wagtail-jev keeps the tags that have a probability at the threshold or higher.
   If you set a maximum number of tags, wagtail-jev keeps only the tags with the highest probabilities.

The result is a list of Suggestions.
Each Suggestion has a tag name and a probability.

This page uses Jev as the backend.
The other backends also give tag suggestions.
Refer to the [README](../README.md#backends).

## Prepare a page model

Make three changes to your page model:

1. Add `JevTaggableMixin`.
2. Put the names of the fields that Jev reads in `jev_text_fields`.
3. Use `JevTagFieldPanel` for the tag field, not `FieldPanel`.

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

The default value of `jev_text_fields` is `("title", "body")`.
The default value of `jev_tag_fields` is `{"tags": JevTagField()}`.

## The button

`JevTagFieldPanel` shows the standard tag widget and the **Let Jev suggest tags** button below it.
The button sends the contents of the form to Jev.
These contents include the changes that the editor did not save.

wagtail-jev adds the new tags to the tag widget.
It does not save the page.
The editor can remove tags before they save the page.

wagtail-jev sends the questions in groups of `WAGTAIL_JEV_BATCH_SIZE` candidate tags.
The default group has 40 tags.
Thus, with 100 candidate tags, one click sends three requests.

## More than one tag field

A page can have more than one tag field.
Give each tag field a `JevTagField` in `jev_tag_fields`.
Each `JevTagField` can have different prompt templates, a different threshold, and different candidate tags.

In the example that follows, `tags` uses the default values.
`feeling_tags` changes three values.
`PromptTemplates` contains the question in three parts.
These parts are the same as the three [prompt templates](#prompt-templates) in the settings.

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

All the arguments of `JevTagField` are optional.
If you do not give an argument, wagtail-jev uses the setting in this table:

| Argument | Setting |
| --- | --- |
| `templates` | `WAGTAIL_JEV_INSTRUCTIONS`, `WAGTAIL_JEV_CRITERIA_TRUE` and `WAGTAIL_JEV_CRITERIA_FALSE` |
| `candidates` | `WAGTAIL_JEV_CANDIDATES`. If this setting is not set, all the tags in the tag model of the field |
| `threshold` | `WAGTAIL_JEV_THRESHOLD` |
| `max_tags` | `WAGTAIL_JEV_MAX_TAGS` |

## Prompt templates

Jev receives one yes/no question for each candidate tag.
Three settings contain the text of that question:

- `WAGTAIL_JEV_INSTRUCTIONS` is the question.
- `WAGTAIL_JEV_CRITERIA_TRUE` is the condition for "yes".
- `WAGTAIL_JEV_CRITERIA_FALSE` is the condition for "no".

These are the default prompt templates for Jev and Clef:

```python
WAGTAIL_JEV_INSTRUCTIONS = (
    "Would an editor file the article in `article` under the tag {tag}? "
    "Judge by the article's actual subject matter, not by incidental mentions."
)
WAGTAIL_JEV_CRITERIA_TRUE = "The article is substantially about, or clearly belongs to, the topic {tag}."
WAGTAIL_JEV_CRITERIA_FALSE = "The topic {tag} is absent or only mentioned in passing."
```

Laya and OpenAI have different default prompt templates.
Refer to [Laya](backends/laya.md) and [OpenAI](backends/openai.md).

In a template, `{tag}` is the name of the tag.
Jev and Clef also receive the page data with these names.
You can use the names in your templates:

- `article` is the page, with a `title` and a `body`.
- `existing_tags` is the list of the existing tags of the page.

To change the prompt templates of one tag field only, give a `templates` argument to its `JevTagField`.
Refer to [More than one tag field](#more-than-one-tag-field).

## Tag many pages

To tag many live pages at the same time, use the `jev_tag_pages` management command:

```sh
manage.py jev_tag_pages blog.ArticlePage
manage.py jev_tag_pages blog.ArticlePage --apply
manage.py jev_tag_pages blog.ArticlePage --apply --publish --threshold 0.8 --ids 12 34
manage.py jev_tag_pages blog.ArticlePage --field feeling_tags
```

The command has these options:

- With no options, the command only shows the Suggestions. It does not change the pages.
- `--apply` adds the tags to a new draft revision of each page.
- `--publish` also publishes that revision. Use it together with `--apply`.
- `--threshold` overrides the threshold of all the tag fields.
- `--max-tags` overrides the maximum number of tags of all the tag fields.
- `--ids` tags only the pages with these IDs.
- `--field` tags only this tag field. You can use `--field` more than one time.
  The default is all the fields in `jev_tag_fields`.

If an error occurs in the request for one page, the command shows the error.
Then it continues with the next page.
If Laya is the backend and Laya cannot start, the command stops immediately.
The command also stops if wagtail-jev cannot connect to the Laya server.

## Use tag suggestions in Python

To get the Suggestions for a saved page, call `jev_suggest_tags()`:

```python
for s in page.jev_suggest_tags("tags"):
    print(s.name, s.probability)
```

You can also get Suggestions for text that is not a saved page:

1. Get the tag field with `jev_tag_field()`.
2. Make an `Article` with a title and a body.
3. Call the `suggest()` method of the tag field with the `Article`.

```python
from wagtail_jev.article import Article

tag_field = ArticlePage.jev_tag_field("tags")
article = Article(title="Django ORM tips", body="select_related and friends")
for s in tag_field.suggest(article):
    print(s.name, s.probability)
```

`suggest()` does the same work as the button.
It ignores the existing tags of the `Article` and gets a probability for each remaining candidate tag.
Then it keeps only the tags at the threshold or higher, to the maximum number of tags.

To get the probability of all the candidate tags, call `tag_field.score(article)`.
`score()` does not use the threshold or the maximum number of tags.
Thus, you can compare different thresholds with the results of one call.

All these methods accept a `client` argument.
If you do not give a client, wagtail-jev opens and closes a connection for each call.
To use one connection for many calls, give the same client to each call:

```python
from wagtail_jev.client import get_client

with get_client() as client:
    for page in ArticlePage.objects.live():
        print(page.title, page.jev_suggest_tags("tags", client=client))
```

## Tune the threshold

1. Start with the default threshold of 0.6.
2. Run `jev_tag_pages` without `--apply` on some pages.
3. Compare the output with the tags that your editors select.
4. If Jev gives incorrect tags, increase the threshold.
5. If Jev does not give correct tags, decrease the threshold or change the prompt templates.

Jev can also read text that is not in English.
But the results are less accurate.
Do a test with the pages of your site.

If you use Jev, set `WAGTAIL_JEV_MODEL` to one version, not `"jev-latest"`, after you tune the threshold.
A new version of Jev can give different probabilities.

# wagtail-jev

wagtail-jev adds two buttons to the edit view of a Wagtail page.
Each button sends the text of the page to an AI decision model.
Then the button shows the result to the editor.

- **Let Jev suggest tags** is below a tag field.
  Jev compares the page with the tags of your site.
  Then wagtail-jev adds the applicable tags to the field.
- **Rate with Jev** gives a Rating of the page, or of one field.
  A Rating shows the level of a Quality that you write, for example readability or mood.
  The editor sees the Rating. wagtail-jev does not save Ratings.

The default model is [Jev](https://docs.typesafe.ai) from TypeSafe.
You can also use Laya, Clef, or OpenAI.
Refer to [Backends](#backends).

https://github.com/user-attachments/assets/e47ef5e2-2a48-4305-b2ed-d1cabf01ba55

## Install

1. Install the package:

   ```sh
   pip install wagtail-jev
   ```

2. Add `wagtail_jev` and your TypeSafe API key to your Django settings:

   ```python
   INSTALLED_APPS = [
       "wagtail_jev",
       ...
   ]

   WAGTAIL_JEV_API_KEY = "..."
   ```

If you do not set `WAGTAIL_JEV_API_KEY`, wagtail-jev uses the `TYPESAFE_API_KEY` environment variable.

## Get tag suggestions

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

    jev_text_fields = ("title", "intro", "body")

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
        JevTagFieldPanel("tags"),
    ]
```

The button sends the contents of the form to Jev.
These contents include the changes that the editor did not save.
wagtail-jev adds the new tags to the tag widget, but it does not save the page.

For more tag fields, the `jev_tag_pages` command, and the Python API, refer to [Tag suggestions](https://github.com/rinti/wagtail-jev/blob/main/doc/tags.md).

## Get Ratings

Write a Quality as a list of levels, from the lowest level to the highest level.
Then add the Quality to `jev_qualities` and add a `JevRatingPanel`:

```python
from wagtail_jev.panels import JevRatingPanel
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


class ArticlePage(JevTaggableMixin, Page):
    ...
    jev_qualities = {"readability": READABILITY}

    content_panels = Page.content_panels + [
        ...
        JevRatingPanel(),
    ]
```

To write a good rubric, get Ratings of one field, or use the Python API, refer to [Qualities and Ratings](https://github.com/rinti/wagtail-jev/blob/main/doc/qualities.md).

## Backends

A backend is the AI decision model that receives the questions from wagtail-jev.
Jev is the default backend.
To use a different backend, set `WAGTAIL_JEV_BACKEND`.
The buttons show the name of the backend, for example **Let Laya suggest tags**.

| Backend | `WAGTAIL_JEV_BACKEND` | Location of the model | Invoices from |
| --- | --- | --- | --- |
| [Jev](https://github.com/rinti/wagtail-jev/blob/main/doc/backends/jev.md) | `"jev"` | TypeSafe | TypeSafe |
| [Laya](https://github.com/rinti/wagtail-jev/blob/main/doc/backends/laya.md) | `"laya"` | Your Django process or your server | None |
| [Clef](https://github.com/rinti/wagtail-jev/blob/main/doc/backends/clef.md) | `"clef"` | Cloudflare Workers AI | Cloudflare |
| [OpenAI](https://github.com/rinti/wagtail-jev/blob/main/doc/backends/openai.md) | `"openai"` | OpenAI Decisions API, public beta | OpenAI |

You can use tag suggestions and Ratings with all the backends.
But in our test, only 10 of 20 Ratings from Laya agreed with the level from an editor.

## Documentation

- [Tag suggestions](https://github.com/rinti/wagtail-jev/blob/main/doc/tags.md)
- [Qualities and Ratings](https://github.com/rinti/wagtail-jev/blob/main/doc/qualities.md)
- [Settings](https://github.com/rinti/wagtail-jev/blob/main/doc/settings.md)
- Backends: [Jev](https://github.com/rinti/wagtail-jev/blob/main/doc/backends/jev.md), [Laya](https://github.com/rinti/wagtail-jev/blob/main/doc/backends/laya.md), [Clef](https://github.com/rinti/wagtail-jev/blob/main/doc/backends/clef.md), [OpenAI](https://github.com/rinti/wagtail-jev/blob/main/doc/backends/openai.md)
- [Development](https://github.com/rinti/wagtail-jev/blob/main/doc/development.md)
- [Changelog](https://github.com/rinti/wagtail-jev/blob/main/CHANGELOG.md)

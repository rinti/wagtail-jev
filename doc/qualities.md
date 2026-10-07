# Qualities and Ratings

A Quality is a property of the text, for example readability or mood.
A Quality is not a tag.

You write a Quality in the page model as a list of levels.
The list starts with the lowest level and stops with the highest level.
This list is the rubric of the Quality.

When an editor clicks the button, Jev selects the level that is most correct for the text.
Jev also gives a probability for each level.
This result is a Rating.
The editor sees the Rating, but wagtail-jev does not save it.

This page uses Jev as the backend.
The other backends also give Ratings.
But in our test, only 10 of 20 Ratings from Laya agreed with the level from an editor.
Refer to [Ratings on Laya](backends/laya.md#ratings-on-laya).

## Write a rubric

You can copy these two Qualities.
The first Quality shows if the text is easy to read.
The second Quality shows the mood of the text.

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

Each level has a short `label` and a longer `description`.
The editor sees the label.
Jev compares the text with the description.
If you do not give a `label` to the Quality, the editor sees the key of the Quality.

Obey these instructions when you write the levels:

- Use 2 to 10 levels. Put the lowest level first.
  If a Quality has a different number of levels, wagtail-jev gives an error when Wagtail loads the panel.
- For each level, write a clear condition of the text or of the reader.
  Do not write only a degree.
  Jev examines each level independently.
  "A reader has to reread a few sentences" is a good description.
  "Moderately readable" is not a good description.
- Write "the text". Do not write "the article" or "the field".
  Then you can use the same Quality for a full page and for one field.

The package does not include rubrics.
Copy the two Qualities in this section and adapt them to your site.

## Add Ratings to the edit view

Add each Quality to `jev_qualities` with a key.
Then add the panels:

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

This example gives three buttons to the editor:

- The button below the intro gives a Rating of the intro for readability.
- The button below the body gives Ratings of the body for readability and mood.
- The `JevRatingPanel` button gives Ratings of the full page for all the Qualities.

### `JevRatingPanel`

`JevRatingPanel` adds a **Rate with Jev** button for the full page.
The button sends the title and all the fields in `jev_text_fields` to Jev.
Jev gives a Rating for each Quality.
The position of the panel in the panel list is not important.

To get Ratings for only some Qualities, give the `keys` argument:

```python
JevRatingPanel(keys=["readability"], heading="Readability")
```

### `JevRatingFieldPanel`

Use `JevRatingFieldPanel` for one text field, not `FieldPanel`.
The field must be a `RichTextField`, a `StreamField`, a `CharField` or a `TextField`.
The button sends only the text of that field.
This text is an Excerpt.
Jev gives a Rating of the Excerpt for each Quality in `keys`.

### Information for the two buttons

This information is applicable to `JevRatingPanel` and to `JevRatingFieldPanel`:

- The button sends the contents of the form to Jev.
  These contents include the changes that the editor did not save.
- The editor sees each Rating on one line, for example `Readability: Easy (62%)`.
  The editor can click the line to see the probability of each level.
- One click sends one request to Jev for all the Qualities of the button.
- If the text is empty, the button does not send a request.
- If a button has only one Quality, the button name includes the Quality, for example **Rate Readability with Jev**.
- An incorrect key causes an error when Wagtail loads the panel.
  A field that Jev cannot read also causes an error at that time.
  Thus, the errors do not occur when an editor clicks the button.

## Use Ratings in Python

A saved page has a `jev_rate()` method.
It returns one Rating for each Quality, from one request to Jev:

```python
for rating in page.jev_rate():
    print(rating.label, rating.top_label, rating.percent)  # Readability Easy 62
```

To get Ratings for only some Qualities, give their keys: `page.jev_rate("readability")`.

Each Rating also contains the probability of each level:

```python
for level, probability in zip(rating.levels, rating.probabilities):
    print(level.label, probability)
```

You can also get Ratings for text that is not a page:

1. Get the Quality with `jev_quality()`.
2. Call its `rate()` method with an `Article` or an `Excerpt`.
   An `Article` has a title and a body.
   An `Excerpt` has only one text.

```python
from wagtail_jev.article import Article, Excerpt

readability = ArticlePage.jev_quality("readability")
readability.rate(Article(title="Django ORM tips", body="select_related and friends"))
readability.rate(Excerpt(text="One dense paragraph."))
readability.rate(Excerpt.from_page(page, "intro"))
```

The last line reads the `intro` field of a saved page.
If the text is empty, `rate()` returns `None`.

To get Ratings of one text for more than one Quality in one request, use `wagtail_jev.quality.rate(qualities, subject)`.
`qualities` is a list of Qualities from `ArticlePage.jev_bound_qualities(*keys)`.

All these functions accept a `client` argument, as the tag functions do.
Refer to [Use tag suggestions in Python](tags.md#use-tag-suggestions-in-python).

## Settings

Qualities do not have a threshold or a maximum number.
There are no settings that are only for Qualities.
Qualities use the same backend, API key, `WAGTAIL_JEV_TIMEOUT` and `WAGTAIL_JEV_MAX_CHARS` as tag suggestions.
Qualities do not change the database.
Thus, no database migration is necessary.
